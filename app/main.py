from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.scheduler import start_scheduler, SINGLE_USER_ID
from app.memory import memory_store
from app.agent import run_agent, AgentState
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi.responses import JSONResponse
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
app = FastAPI(title="Exercise Coach Agent", version="1.0.0", lifespan=lifespan)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://daec2ff92480.ngrok-free.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
    expose_headers=["*"],
    max_age=3600,
)
# Explicit OPTIONS handlers
@app.options("/chat")
async def options_chat():
    return JSONResponse(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000,https://daec2ff92480.ngrok-free.app",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,Accept,X-Requested-With",
            "Access-Control-Max-Age": "3600",
        },
    )
@app.options("/coach/chat")
async def options_coach_chat():
    return JSONResponse(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000,https://0174a2412b84.ngrok-free.app",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,Accept,X-Requested-With",
            "Access-Control-Max-Age": "3600",
        },
    )
class ChatMessage(BaseModel):
    message: str
class CoachMessage(BaseModel):
    user_id: str
    prompt: str
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
# coach endpoints
@app.get("/coach-commands")
def get_coach_commands(user_id: str, coach_id: str):
    """Get coach instructions from ChromaDB."""
    user_data = memory_store.get(user_id)
    instruction = user_data.get("coach_instruction", {
        "instruction_id": "default_123",
        "coach_id": coach_id,
        "user_id": user_id,
        "prompt": "Motivate the user to stay consistent.",
        "timestamp": datetime.now().isoformat()
    })
    return instruction
@app.post("/coach/chat")
def coach_chat(message: CoachMessage):
    """Coach sends instruction to user."""
    instruction = {
        "instruction_id": f"coach_{datetime.now().timestamp()}",
        "coach_id": "coach_001",
        "user_id": message.user_id,
        "prompt": message.prompt,
        "timestamp": datetime.now().isoformat()
    }
    memory_store.update(message.user_id, {"coach_instruction": instruction})
    return {"status": "instruction sent", "instruction": instruction}
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