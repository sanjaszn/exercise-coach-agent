from fastapi import FastAPI
from app.scheduler import start_scheduler, set_user_schedule, SINGLE_USER_ID
from app.memory import memory_store
from app.agent import run_agent, AgentState
from contextlib import asynccontextmanager

# Creates ONE background job for the scheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield

app = FastAPI(title="Single User Exercise Coach", version="1.0.0", lifespan=lifespan)

@app.post("/schedule")
def schedule_exercise(time: str):
    """Schedule daily exercise time."""
    set_user_schedule(time)
    return {"message": f"Scheduled daily exercise at {time}"}

@app.post("/feedback")
def submit_feedback(feedback: str):
    """Submit feedback for completed exercise."""
    memory_store.update(SINGLE_USER_ID, {"feedback": feedback})
    return {"message": "Feedback received! Thanks for completing your exercise."}

@app.get("/status")
def get_status():
    """Get current status."""
    session = memory_store.get(SINGLE_USER_ID)
    
    if not session:
        return {"status": "not_scheduled", "message": "No schedule set"}
    
    if not session.get("last_exercise"):
        status = "scheduled"
    elif not session.get("feedback"):
        status = "waiting_feedback" 
    else:
        status = "completed"
    
    return {
        "status": status,
        "scheduled_time": session.get("scheduled_time"),
        "last_exercise": session.get("last_exercise"),
        "feedback": session.get("feedback"),
        "reminders_sent": session.get("reminders_sent", 0)
    }

@app.post("/test-now")
def test_now():
    """Test run agent right now."""
    state = AgentState(
        input="",
        user_id=SINGLE_USER_ID,
        coach_id="coach123",
        node_output="", 
        output=""
    )
    result = run_agent(state)
    return {"message": result}

@app.post("/reset")
def reset_session():
    """Reset session."""
    memory_store.clear(SINGLE_USER_ID)
    return {"message": "Session reset"}

@app.get("/")
def root():
    return {"message": "Single User Exercise Coach - Agent runs every hour!"}