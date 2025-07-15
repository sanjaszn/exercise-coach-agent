# app/agent.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from app.routing import route_input
from app.tools import send_exercise_fn, send_reminder_fn, check_feedback_fn
from app.scheduler import schedule_session_fn
from app.memory import memory_store
import os
from dotenv import load_dotenv

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

# Nodes
def send_exercise_node(state: AgentState) -> dict:
    """Send a new exercise to the user."""
    user_id = state["user_id"]
    result = send_exercise_fn(user_id)  # From tools.py
    memory_store.update(user_id, {"last_exercise": result, "reminders_sent": 0})
    return {"node_output": f"Here's your daily exercise: {result}"}

def send_reminder_node(state: AgentState) -> dict:
    """Send a reminder if feedback is missing."""
    user_id = state["user_id"]
    session = memory_store.get(user_id) or {}
    reminders = session.get("reminders_sent", 0)
    if reminders < 3:
        result = send_reminder_fn(user_id)  # From tools.py
        memory_store.update(user_id, {"reminders_sent": reminders + 1})
        return {"node_output": f"Reminder: {result}"}
    else:
        result = check_feedback_fn(user_id)  # From tools.py
        return {"node_output": result}

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

# Routing function
def route_to_node(state: AgentState) -> str:
    """Route input to appropriate node."""
    # Stop if output is already set (after finalize)
    if state.get("output"):
        return END
    
    user_id = state["user_id"]
    session = memory_store.get(user_id) or {}  # Ensure session is not None
    user_input = state["input"].lower()

    # Route based on input intent first - UPDATED to pass user_id
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

    # Fallback to state-based routing
    if not session.get("last_exercise"):
        return "send_exercise"
    elif not session.get("feedback") and session.get("reminders_sent", 0) < 3:
        return "send_reminder"
    elif not session.get("feedback"):
        return "check_feedback"
    
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