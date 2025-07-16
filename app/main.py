from fastapi import FastAPI
from pydantic import BaseModel
from app.scheduler import start_scheduler, SINGLE_USER_ID
from app.memory import memory_store
from app.agent import run_agent, AgentState
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield

app = FastAPI(title="Exercise Coach Agent", version="1.0.0", lifespan=lifespan)

class ChatMessage(BaseModel):
    message: str

# main chat endpoint
@app.post("/chat")
def chat_with_agent(chat: ChatMessage):
    """Take input, run agent."""
    state = AgentState(
        input=chat.message,
        user_id=SINGLE_USER_ID,
        coach_id="coach123",
        node_output="", 
        output=""
    )
    result = run_agent(state)
    return {"response": result}

@app.get("/status")
def get_status():
    session = memory_store.get(SINGLE_USER_ID)
    if not session:
        return {"status": "not_scheduled"}
    
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

@app.post("/reset")
def reset_session():
    memory_store.clear(SINGLE_USER_ID)
    return {"message": "Session reset"}

@app.get("/")
def root():
    return {"message": "Exercise Coach Agent - Send messages to /chat"}