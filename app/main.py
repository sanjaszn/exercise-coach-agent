from fastapi import FastAPI, HTTPException
from models import ScheduleRequest, RunNowRequest, FeedbackRequest, StatusResponse
from scheduler import schedule_user_job, cancel_user_job, run_now, handle_feedback_received
from memory import memory_store
from agent_runner import run_agent_session

app = FastAPI()

@app.post("/schedule")
def schedule_exercise(req: ScheduleRequest):
    """Schedule daily exercise for a user."""
    schedule_user_job(req.user_id, req.time)
    return {"message": f"Exercise scheduled for {req.time} for user {req.user_id}."}

@app.post("/run-now")
def run_now_endpoint(req: RunNowRequest):
    """Run agent session immediately for a user."""
    response = run_now(req.user_id)
    return {"message": response}

@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    """Submit feedback for completed exercise."""
    session = memory_store.get(req.user_id)
    if not session.get("last_exercise"):
        raise HTTPException(status_code=400, detail="No exercise sent yet.")
    
    # Update memory with feedback
    memory_store.update(req.user_id, {"feedback": req.feedback})
    
    # Cancel any pending reminders
    handle_feedback_received(req.user_id)
    
    # Get agent response
    response = run_agent_session(req.user_id)
    return {"message": response}

@app.get("/status", response_model=StatusResponse)
def get_status(user_id: str):
    """Get current status of user's exercise session."""
    session = memory_store.get(user_id)
    if not session:
        raise HTTPException(status_code=404, detail="User session not found.")
    
    # Determine status
    if not session.get("last_exercise"):
        status = "no exercise"
    elif not session.get("feedback"):
        status = "waiting for feedback"
    else:
        status = "completed"
    
    return StatusResponse(
        user_id=user_id,
        scheduled_time=session.get("scheduled_time"),
        last_exercise=session.get("last_exercise"),
        feedback=session.get("feedback"),
        reminders_sent=session.get("reminders_sent", 0),
        status=status
    )

@app.delete("/schedule")
def delete_schedule(user_id: str):
    """Cancel scheduled exercise for a user."""
    cancel_user_job(user_id)
    return {"message": f"Schedule cancelled for user {user_id}."}

@app.post("/reset")
def reset_user_session(user_id: str):
    """Reset user session (for testing/debugging)."""
    memory_store.clear(user_id)
    cancel_user_job(user_id)
    return {"message": f"Session reset for user {user_id}."}

@app.get("/")
def root():
    """Health check endpoint."""
    return {"message": "Fitness Coach Agent API is running!"}