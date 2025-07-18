from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from app.routing import route_input
from app.tools import send_exercise_fn, send_reminder_fn, check_feedback_fn
from app.scheduler import schedule_session_fn
from app.memory import memory_store
from app.coach import fetch_coach_instructions, parse_coach_prompt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load .env
load_dotenv()

# Initialize DeepSeek LLM with timeout
llm = ChatOpenAI(
    model="deepseek/deepseek-chat-v3-0324:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0.2,
    max_tokens=1000,
    timeout=30,
)

# Define AgentState
class AgentState(TypedDict):
    input: str
    user_id: str
    coach_id: str
    node_output: str
    output: str

def send_exercise_node(state: AgentState) -> dict:
    """Send a new exercise to the user, tailored by coach instructions."""
    user_id = state["user_id"]
    coach_id = state["coach_id"]
    
    instruction = fetch_coach_instructions(user_id, coach_id)
    parsed_instruction = parse_coach_prompt(instruction.get("prompt", ""))
    
    session = memory_store.get(user_id) or {}
    user_goals = session.get("goals", "your fitness goals")
    
    try:
        result = send_exercise_fn(user_id)
        memory_store.update(user_id, {"last_exercise": result, "reminders_sent": 0})
        
        message = f"Here's your daily exercise: {result}"
        if parsed_instruction["include_goals"]:
            message += f"\nKeep working toward {user_goals}!"
        if parsed_instruction["warning_tone"]:
            message += "\nStay consistent to avoid falling behind!"
        logger.debug(f"send_exercise_node: {message}")
        return {"node_output": message}
    except Exception as e:
        logger.error(f"send_exercise_node error: {str(e)}")
        return {"node_output": f"Error sending exercise: {str(e)}"}

def send_reminder_node(state: AgentState) -> dict:
    """Send a reminder if feedback is missing, tailored by coach instructions."""
    user_id = state["user_id"]
    coach_id = state["coach_id"]
    session = memory_store.get(user_id) or {}
    reminders = session.get("reminders_sent", 0)
    
    instruction = fetch_coach_instructions(user_id, coach_id)
    parsed_instruction = parse_coach_prompt(instruction.get("prompt", ""))
    
    user_goals = session.get("goals", "your fitness goals")
    last_exercise_date = session.get("last_exercise_date")
    warning_triggered = False
    if last_exercise_date and parsed_instruction["warning_tone"]:
        days_since = (datetime.now().date() - datetime.fromisoformat(last_exercise_date).date()).days
        warning_triggered = days_since >= 3
    
    try:
        result = send_reminder_fn(user_id)
        message = result
        if parsed_instruction["include_goals"]:
            message += f"\nThis will help you reach {user_goals}."
        if warning_triggered:
            message += "\nWarning: You haven't exercised in over 3 days. Get back on track!"
        memory_store.update(user_id, {"reminders_sent": reminders + 1})
        logger.debug(f"send_reminder_node: {message}")
        return {"node_output": message}
    except Exception as e:
        logger.error(f"send_reminder_node error: {str(e)}")
        return {"node_output": f"Error sending reminder: {str(e)}"}

def check_feedback_node(state: AgentState) -> dict:
    """Check user feedback and thank them."""
    user_id = state["user_id"]
    try:
        result = check_feedback_fn(user_id)
        if result != "No feedback yet":
            message = f"Thanks for completing your exercise! Your feedback: '{result}'"
        else:
            message = "Still waiting for your feedback. Please let me know when you're done!"
        logger.debug(f"check_feedback_node: {message}")
        return {"node_output": message}
    except Exception as e:
        logger.error(f"check_feedback_node error: {str(e)}")
        return {"node_output": f"Error checking feedback: {str(e)}"}

def schedule_node(state: AgentState) -> dict:
    """Schedule a workout session."""
    user_id = state["user_id"]
    try:
        input_lower = state["input"].lower()
        # Match time formats like "10:00", "10:00 am", "10:00pm", or "at 10:00"
        time_match = re.search(r'(?:\bat\s+)?(\d{1,2}:\d{2}\s*(?:[ap]m)?)', input_lower, re.IGNORECASE)
        time_str = time_match.group(1).strip() if time_match else "12:00"
        # Validate and parse time
        try:
            if "am" in time_str.lower() or "pm" in time_str.lower():
                parsed_time = datetime.strptime(time_str, "%I:%M %p")
            else:
                parsed_time = datetime.strptime(time_str, "%H:%M")
            hour, minute = parsed_time.hour, parsed_time.minute
        except ValueError:
            logger.error(f"Invalid time format: {time_str}")
            time_str = "12:00"
            hour, minute = 12, 0
        result = schedule_session_fn(user_id, time_str)
        memory_store.update(user_id, {
            "scheduled_time": time_str,
            "scheduled_hour": hour,
            "scheduled_minute": minute
        })
        message = f"Session scheduled for {time_str}: {result}"
        logger.debug(f"schedule_node: {message}")
        return {"node_output": message}
    except Exception as e:
        logger.error(f"schedule_node error: {str(e)}")
        return {"node_output": f"Error scheduling session: {str(e)}"}

def answer_workout_question_node(state: AgentState) -> dict:
    """Answer workout-related questions using LLM."""
    user_id = state["user_id"]
    question = state["input"]
    try:
        response = llm.invoke(f"Answer this workout question: {question}")
        logger.debug(f"LLM response: {response.content}")
        return {"node_output": response.content}
    except Exception as e:
        logger.error(f"LLM error: {str(e)}")
        return {"node_output": f"Error answering question: {str(e)}"}

def finalize_node(state: AgentState) -> dict:
    """Add viral loop and finalize response."""
    try:
        node_output = state.get("node_output", "")
        coach_id = state["coach_id"]
        viral_text = f"\nPowered by MyAgentsAI: https://myagents.ai/signup?ref={coach_id}"
        logger.debug(f"finalize_node: {node_output}{viral_text}")
        return {"output": f"{node_output}{viral_text}"}
    except Exception as e:
        logger.error(f"finalize_node error: {str(e)}")
        return {"output": f"Error finalizing response: {str(e)}"}

def route_to_node(state: AgentState) -> str:
    """Route input to appropriate node, considering coach instructions."""
    logger.debug(f"Routing state: {state}")
    try:
        if state.get("output"):
            logger.debug("Output exists, returning END")
            return END
        
        user_id = state["user_id"]
        coach_id = state["coach_id"]
        session = memory_store.get(user_id) or {}
        user_input = state["input"].lower()
        logger.debug(f"Session: {session}")
        
        instruction = fetch_coach_instructions(user_id, coach_id)
        parsed_instruction = parse_coach_prompt(instruction.get("prompt", ""))
        logger.debug(f"Parsed instruction: {parsed_instruction}")
        
        intent = route_input(user_input, user_id)
        logger.debug(f"Intent: {intent}")
        if intent == "schedule":
            logger.debug("Routing to schedule")
            return "schedule"
        elif intent == "question":
            logger.debug("Routing to answer_workout_question")
            return "answer_workout_question"
        elif intent == "check_feedback":
            logger.debug("Routing to check_feedback")
            return "check_feedback"
        elif intent == "send_reminder":
            logger.debug("Routing to send_reminder")
            return "send_reminder"
        elif intent == "send_exercise":
            logger.debug("Routing to send_exercise")
            return "send_exercise"
        
        if not session.get("last_exercise"):
            logger.debug("No last_exercise, routing to send_exercise")
            return "send_exercise"
        if not session.get("feedback"):
            if session.get("reminders_sent", 0) < 3 and parsed_instruction["warning_tone"] and session.get("last_exercise_date"):
                try:
                    days_since = (datetime.now().date() - datetime.fromisoformat(session["last_exercise_date"]).date()).days
                    logger.debug(f"Days since: {days_since}, Warning tone: {parsed_instruction['warning_tone']}, Reminders sent: {session.get('reminders_sent', 0)}")
                    if days_since >= 3:
                        logger.debug("Routing to send_reminder due to warning and inactivity")
                        return "send_reminder"
                except ValueError as e:
                    logger.error(f"Date parsing error: {e}")
            if session.get("reminders_sent", 0) < 3:
                logger.debug("Routing to send_reminder due to no feedback and reminders < 3")
                return "send_reminder"
            logger.debug("Routing to check_feedback due to max reminders or no warning")
            return "check_feedback"
        
        logger.debug("Default routing to send_exercise")
        return "send_exercise"
    except Exception as e:
        logger.error(f"route_to_node error: {str(e)}")
        return END

def build_graph():
    try:
        graph = StateGraph(AgentState)
        graph.add_node("send_exercise", send_exercise_node)
        graph.add_node("send_reminder", send_reminder_node)
        graph.add_node("check_feedback", check_feedback_node)
        graph.add_node("schedule", schedule_node)
        graph.add_node("answer_workout_question", answer_workout_question_node)
        graph.add_node("finalize", finalize_node)
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
        graph.add_edge("send_exercise", "finalize")
        graph.add_edge("send_reminder", "finalize")
        graph.add_edge("check_feedback", "finalize")
        graph.add_edge("schedule", "finalize")
        graph.add_edge("answer_workout_question", "finalize")
        graph.set_entry_point("send_exercise")
        graph.set_finish_point("finalize")
        logger.debug("Graph built successfully")
        return graph.compile()
    except Exception as e:
        logger.error(f"build_graph error: {str(e)}")
        raise

def run_agent(state: AgentState) -> str:
    """Run the agent with the given state."""
    try:
        graph = build_graph()
        logger.debug(f"Invoking graph with state: {state}")
        result = graph.invoke(state)
        logger.debug(f"run_agent result: {result}")
        return result["output"]
    except Exception as e:
        logger.error(f"run_agent error: {str(e)}")
        raise