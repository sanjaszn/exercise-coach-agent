from apscheduler.schedulers.background import BackgroundScheduler
from app.memory import memory_store
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

scheduler = BackgroundScheduler()

def get_active_sessions():
    """Get all active sessions from memory store."""
    sessions = memory_store.get_all_sessions()
    active_sessions = []
    
    for session in sessions:
        user_id = session["user_id"]
        session_data = session["session_data"]
        
        # Consider a session active if it has scheduled time or last exercise
        if session_data.get("scheduled_time") or session_data.get("last_exercise"):
            # Extract agent_id from user_id (format: "end_user_{agent_id}")
            if user_id.startswith("end_user_"):
                agent_id = user_id.replace("end_user_", "")
                active_sessions.append({
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "session_data": session_data
                })
    
    return active_sessions

def hourly_agent_run():
    """Run agent for all active sessions every hour."""
    print(f"Running hourly check at {datetime.now()}")
    
    # Import here to avoid circular imports
    from app.agent import run_agent, AgentState
    
    # Get active sessions from memory store
    active_sessions = get_active_sessions()
    
    if not active_sessions:
        print("No active sessions found")
        return
    
    for session in active_sessions:
        try:
            user_id = session.get("user_id")
            agent_id = session.get("agent_id")
            
            if not user_id or not agent_id:
                continue
                
            print(f"Checking user {user_id} with agent {agent_id}")
            state = AgentState(
                input="",
                user_id=user_id,
                agent_owner_id=agent_id,
                node_output="",
                output=""
            )
            result = run_agent(state)
            print(f"Result for {user_id}: {result}")
        except Exception as e:
            print(f"Error processing session {session}: {e}")

def start_scheduler():
    """Start the hourly scheduler."""
    scheduler.add_job(
        hourly_agent_run,
        'interval',
        hours=1,
        id='hourly_agent_check'
    )
    scheduler.start()
    print("Scheduler started - agent will run every hour for active sessions")

def set_user_schedule(user_id: str, time_str: str):
    """Set schedule for a specific user."""
    hour, minute = map(int, time_str.split(":"))
    memory_store.update(user_id, {
        "scheduled_hour": hour,
        "scheduled_minute": minute,
        "scheduled_time": time_str
    })
    print(f"User {user_id} scheduled for {time_str}")

def schedule_session_fn(user_id: str, time_str: str) -> str:
    """Schedule a workout session (used by agent)."""
    set_user_schedule(user_id, time_str)
    return f"Scheduled for {time_str} daily"

def run_agent_for_user(user_id: str, agent_owner_id: str, input_message: str = ""):
    """Run agent for a specific user and agent owner."""
    from app.agent import run_agent, AgentState
    
    try:
        print(f"Running agent for user {user_id} with agent owner {agent_owner_id}")
        state = AgentState(
            input=input_message,
            user_id=user_id,
            agent_owner_id=agent_owner_id,
            node_output="",
            output=""
        )
        result = run_agent(state)
        print(f"Result: {result}")
        return result
    except Exception as e:
        print(f"Error running agent for user {user_id}: {e}")
        return None