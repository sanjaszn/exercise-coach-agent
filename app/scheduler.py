from apscheduler.schedulers.background import BackgroundScheduler
from app.memory import memory_store
from datetime import datetime

scheduler = BackgroundScheduler()

# Single user ID - could be from env or config
SINGLE_USER_ID = "user123"

def hourly_agent_run():
    """Run agent for the single user every hour."""
    print(f"Running hourly check at {datetime.now()}")
    
    # Import here to avoid circular imports
    from app.agent import run_agent, AgentState
    
    try:
        print(f"Checking user {SINGLE_USER_ID}")
        state = AgentState(
            input="",
            user_id=SINGLE_USER_ID,
            coach_id="coach123", 
            node_output="",
            output=""
        )
        result = run_agent(state)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

def start_scheduler():
    """Start the hourly scheduler."""
    scheduler.add_job(
        hourly_agent_run,
        'interval',
        hours=1,
        id='hourly_agent'
    )
    scheduler.start()
    print("Scheduler started - agent will run every hour for single user")

def set_user_schedule(time_str: str):
    """Set schedule for the single user."""
    hour, minute = map(int, time_str.split(":"))
    memory_store.update(SINGLE_USER_ID, {
        "scheduled_hour": hour,
        "scheduled_minute": minute,
        "scheduled_time": time_str
    })
    print(f"User scheduled for {time_str}")

def schedule_session_fn(user_id: str, time_str: str) -> str:
    """Schedule a workout session (used by agent)."""
    set_user_schedule(time_str)
    return f"Scheduled for {time_str} daily"