from fastapi import FastAPI, HTTPException
from models import ScheduleRequest, RunNowRequest, FeedbackRequest, StatusResponse
from scheduler import schedule_user_job, cancel_user_job, run_now
from memory import memory_store
from agent_runner import run_agent_session

app = FastAPI()

@app.post("/schedule")
def schedule_exercise(req: ScheduleRequest):
    schedule_user_job(req.user_id, req.time)
    return {"message": f"Exercise scheduled for {req.time} for user {req.user_id}."}

@app.post("/run-now")
def run_now_endpoint(req: RunNowRequest):
    response = run_now(req.user_id)
    return {"message": response}

@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    session = memory_store.get(req.user_id)
    if not session.get("last_exercise"):
        raise HTTPException(status_code=400, detail="No exercise sent yet.")
    memory_store.update(req.user_id, {"feedback": req.feedback})
    response = run_agent_session(req.user_id)
    return {"message": response}

@app.get("/status", response_model=StatusResponse)
def get_status(user_id: str):
    session = memory_store.get(user_id)
    if not session:
        raise HTTPException(status_code=404, detail="User session not found.")
    return StatusResponse(
        user_id=user_id,
        scheduled_time=session.get("scheduled_time"),
        last_exercise=session.get("last_exercise"),
        feedback=session.get("feedback"),
        reminders_sent=session.get("reminders_sent", 0),
        status="waiting for feedback" if not session.get("feedback") else "completed"
    )

@app.delete("/schedule")
def delete_schedule(user_id: str):
    cancel_user_job(user_id)
    return {"message": f"Schedule cancelled for user {user_id}."} 