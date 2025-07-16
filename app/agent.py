from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from app.routing import route_input
from app.tools import send_exercise_fn, send_reminder_fn, check_feedback_fn
from app.scheduler import schedule_session_fn
from app.memory import memory_store
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# Load .env
load_dotenv()

# Initialize DeepSeek LLM via OpenRouter
llm = ChatOpenAI(
    model="deepseek/deepseek-chat-v3-0324:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0.2,
    max_tokens=1000
)

# Define AgentState
class AgentState(TypedDict):
    input: str
    user_id: str
    coach_id: str
    node_output: str  # Intermediate output from nodes
    output: str       # Final output after finalize

def fetch_coach_instructions(user_id: str, coach_id: str) -> dict:
    """Fetch coach instructions from API and cache them."""
    session = memory_store.get(user_id) or {}
    last_fetched = session.get("last_instruction_fetch")
    now = datetime.now()
    
    # Fetch only if not fetched in the last hour
    if not last_fetched or (now - datetime.fromisoformat(last_fetched)).total_seconds() > 3600:
        try:
            response = requests.get(
                f"https://api.myagents.ai/coach-commands?user_id={user_id}&coach_id={coach_id}",
                headers={"Authorization": f"Bearer {os.getenv('API_TOKEN')}"}
            )
            response.raise_for_status()
            instruction = response.json()
            memory_store.update(user_id, {
                "coach_instruction": instruction,
                "last_instruction_fetch": now.isoformat()
            })
            return instruction
        except requests.RequestException:
            # Fallback to cached instruction or default
            return session.get("coach_instruction", {"prompt": "Motivate the user to stay consistent."})
    return session.get("coach_instruction", {"prompt": "Motivate the user to stay consistent."})

def parse_coach_prompt(prompt: str) -> dict:
    """Parse coach prompt to extract intent and details."""
    prompt = prompt.lower()
    result = {
        "motivation_type": "general",  # Default
        "include_goals": False,
        "warning_tone": False
    }
    
    if "goal" in prompt:
        result["motivation_type"] = "goal_reminder"
        result["include_goals"] = True
    if "warn" in prompt or "lack of exercise" in prompt:
        result["motivation_type"] = "warning"
        result["warning_tone"] = True
    
    return result

def send_exercise_node(state: AgentState) -> dict:
    """Send a new exercise to the user, tailored by coach instructions."""
    user_id = state["user_id"]
    coach_id = state["coach_id"]
    
    # Fetch and parse coach instructions
    instruction = fetch_coach_instructions(user_id, coach_id)
    parsed_instruction = parse_coach_prompt(instruction.get("prompt", ""))
    
    # Get user context (e.g., goals)
    session = memory_store.get(user_id) or {}
    user_goals = session.get("goals", "your fitness goals")
    
    # Send exercise
    result = send_exercise_fn(user_id)  # From tools.py
    memory_store.update(user_id, {"last_exercise": result, "reminders_sent": 0})
    
    # Customize message based on coach instructions
    message = f"Here's your daily exercise: {result}"
    if parsed_instruction["include_goals"]:
        message += f"\nKeep working toward {user_goals}!"
    if parsed_instruction["warning_tone"]:
        message += "\nStay consistent to avoid falling behind!"
    
    return {"node_output": message}

def send_reminder_node(state: AgentState) -> dict:
    """Send a reminder if feedback is missing, tailored by coach instructions."""
    user_id = state["user_id"]
    coach_id = state["coach_id"]
    session = memory_store.get(user_id) or {}
    reminders = session.get("reminders_sent", 0)
    
    # Fetch and parse coach instructions
    instruction = fetch_coach_instructions(user_id, coach_id)
    parsed_instruction = parse_coach_prompt(instruction.get("prompt", ""))
    
    # Get user context
    user_goals = session.get("goals", "your fitness goals")
    last_exercise_date = session.get("last_exercise_date")
    warning_triggered = False
    if last_exercise_date and parsed_instruction["warning_tone"]:
        days_since = (datetime.now().date() - datetime.fromisoformat(last_exercise_date).date()).days
        warning_triggered = days_since >= 3
    
    result = send_reminder_fn(user_id)  # From tools.py
    message = result
    if parsed_instruction["include_goals"]:
        message += f"\nThis will help you reach {user_goals}."
    if warning_triggered:
        message += "\nWarning: You haven't exercised in over 3 days. Get back on track!"
    memory_store.update(user_id, {"reminders_sent": reminders + 1})
    return {"node_output": message}

def check_feedback_node(state: AgentState) -> dict:
    """Check user feedback and thank them."""
    user_id = state["user_id"]
    result = check_feedback_fn(user_id)  # From tools.py
    if result != "No feedback yet":
        return {"node_output": f"Thanks for completing your exercise! Your feedback: '{result}'"}
    return {"node_output": "Still waiting for your feedback. Please let me know when you're done!"}

def schedule_node(state: AgentState) -> dict:
    """Schedule a workout session."""
    user_id = state["user_id"]
    time_str = state["input"].split("at")[-1].strip() if "at" in state["input"] else "12:00"
    result = schedule_session_fn(user_id, time_str)  # From scheduler.py
    memory_store.update(user_id, {"scheduled_time": time_str})
    return {"node_output": f"Session scheduled for {time_str}: {result}"}

def answer_workout_question_node(state: AgentState) -> dict:
    """Answer workout-related questions using LLM."""
    user_id = state["user_id"]
    question = state["input"]
    response = llm.invoke(f"Answer this workout question: {question}")
    return {"node_output": response.content}

def finalize_node(state: AgentState) -> dict:
    """Add viral loop and finalize response."""
    node_output = state.get("node_output", "")
    coach_id = state["coach_id"]
    viral_text = f"\nPowered by MyAgentsAI: https://myagents.ai/signup?ref={coach_id}"
    return {"output": f"{node_output}{viral_text}"}

def route_to_node(state: AgentState) -> str:
    """Route input to appropriate node, considering coach instructions."""
    if state.get("output"):
        return END
    
    user_id = state["user_id"]
    coach_id = state["coach_id"]
    session = memory_store.get(user_id) or {}
    user_input = state["input"].lower()
    
    # Fetch coach instructions to influence routing
    instruction = fetch_coach_instructions(user_id, coach_id)
    parsed_instruction = parse_coach_prompt(instruction.get("prompt", ""))
    
    # Route based on input intent first
    intent = route_input(user_input, user_id)  # From routing.py
    if intent == "schedule":
        return "schedule"
    elif intent == "question":
        return "answer_workout_question"
    elif intent == "check_feedback":
        return "check_feedback"
    elif intent == "send_reminder":
        return "send_reminder"
    elif intent == "send_exercise":
        return "send_exercise"
    
    # Fallback to state-based routing, influenced by coach instructions
    if not session.get("last_exercise"):
        return "send_exercise"
    if not session.get("feedback") and session.get("reminders_sent", 0) < 3:
        if parsed_instruction["warning_tone"] and session.get("last_exercise_date"):
            days_since = (datetime.now().date() - datetime.fromisoformat(session["last_exercise_date"]).date()).days
            if days_since >= 3:
                return "send_reminder"  # Prioritize reminder for inactivity with warning
        return "send_reminder"  # Send reminder if feedback missing and reminders not maxed
    if not session.get("feedback"):
        return "check_feedback"  # Check feedback if max reminders sent or no warning
    
    return "send_exercise"  # Default

# Build the graph
def build_graph():
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("send_exercise", send_exercise_node)
    graph.add_node("send_reminder", send_reminder_node)
    graph.add_node("check_feedback", check_feedback_node)
    graph.add_node("schedule", schedule_node)
    graph.add_node("answer_workout_question", answer_workout_question_node)
    graph.add_node("finalize", finalize_node)
    
    # Add conditional edges
    graph.add_conditional_edges(
        "send_exercise", route_to_node, 
        {
            "send_exercise": "send_exercise",
            "send_reminder": "send_reminder",
            "check_feedback": "check_feedback",
            "schedule": "schedule",
            "answer_workout_question": "answer_workout_question",
            END: END
        }
    )
    graph.add_conditional_edges(
        "send_reminder", route_to_node, 
        {
            "send_exercise": "send_exercise",
            "send_reminder": "send_reminder",
            "check_feedback": "check_feedback",
            "schedule": "schedule",
            "answer_workout_question": "answer_workout_question",
            END: END
        }
    )
    graph.add_conditional_edges(
        "check_feedback", route_to_node, 
        {
            "send_exercise": "send_exercise",
            "send_reminder": "send_reminder",
            "check_feedback": "check_feedback",
            "schedule": "schedule",
            "answer_workout_question": "answer_workout_question",
            END: END
        }
    )
    graph.add_conditional_edges(
        "schedule", route_to_node, 
        {
            "send_exercise": "send_exercise",
            "send_reminder": "send_reminder",
            "check_feedback": "check_feedback",
            "schedule": "schedule",
            "answer_workout_question": "answer_workout_question",
            END: END
        }
    )
    graph.add_conditional_edges(
        "answer_workout_question", route_to_node, 
        {
            "send_exercise": "send_exercise",
            "send_reminder": "send_reminder",
            "check_feedback": "check_feedback",
            "schedule": "schedule",
            "answer_workout_question": "answer_workout_question",
            END: END
        }
    )
    
    # Always finalize
    graph.add_edge("send_exercise", "finalize")
    graph.add_edge("send_reminder", "finalize")
    graph.add_edge("check_feedback", "finalize")
    graph.add_edge("schedule", "finalize")
    graph.add_edge("answer_workout_question", "finalize")
    
    # Set entry and finish points
    graph.set_entry_point("send_exercise")
    graph.set_finish_point("finalize")
    
    return graph.compile()

# Main execution function
def run_agent(state: AgentState) -> str:
    """Run the agent with the given state."""
    graph = build_graph()
    result = graph.invoke(state)
    return result["output"]