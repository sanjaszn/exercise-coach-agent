from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.scheduler import start_scheduler
from app.memory import memory_store
from app.agent import run_agent, AgentState
from app.agent_creator import create_agent_from_description
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi.responses import JSONResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield

app = FastAPI(title="Exercise Agent Platform", version="2.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://daec2ff92480.ngrok-free.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
    expose_headers=["*"],
    max_age=3600,
)

# Models
class ChatMessage(BaseModel):
    message: str

class AgentOwnerMessage(BaseModel):
    end_user_id: str
    prompt: str

class CreateAgentRequest(BaseModel):
    description: str

# Agent Creation Endpoint
@app.post("/create-agent")
def create_agent(request: CreateAgentRequest):
    """Create a new agent from user description"""
    try:
        return create_agent_from_description(request.description)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

# End User Chat Endpoint
@app.post("/end-user/chat/{agent_id}")
def chat_with_agent(agent_id: str, chat: ChatMessage):
    """Chat with a specific agent - for end users"""
    state = AgentState(
        input=chat.message,
        user_id=f"end_user_{agent_id}",  # One session per agent
        agent_owner_id=agent_id,
        node_output="",
        output=""
    )
    result = run_agent(state)
    return {"response": result, "agent_id": agent_id}

# Agent Owner Commands Endpoint
@app.post("/agent-owner/chat/{agent_id}")
def agent_owner_chat(agent_id: str, message: AgentOwnerMessage):
    """Send instruction to specific agent - for agent owners"""
    instruction = {
        "instruction_id": f"owner_{datetime.now().timestamp()}",
        "agent_id": agent_id,
        "end_user_id": message.end_user_id,
        "prompt": message.prompt,
        "timestamp": datetime.now().isoformat()
    }
    # Store agent owner instructions in the same session as end user data
    memory_store.update(f"end_user_{agent_id}", {"agent_owner_instruction": instruction})
    return {"status": "instruction sent", "instruction": instruction, "agent_id": agent_id}



# Utility endpoints
@app.get("/status/{agent_id}")
def get_agent_status(agent_id: str):
    """Get status for specific agent"""
    session = memory_store.get(f"end_user_{agent_id}")
    if not session:
        return {"status": "not_scheduled", "agent_id": agent_id}
    
    if not session.get("last_exercise"):
        status = "scheduled"
    elif not session.get("feedback"):
        status = "waiting_feedback"
    else:
        status = "completed"
    
    return {
        "status": status,
        "agent_id": agent_id,
        "scheduled_time": session.get("scheduled_time"),
        "last_exercise": session.get("last_exercise"),
        "feedback": session.get("feedback"),
        "reminders_sent": session.get("reminders_sent", 0)
    }

@app.post("/reset/{agent_id}")
def reset_agent_session(agent_id: str):
    """Reset session for specific agent"""
    memory_store.clear(f"end_user_{agent_id}")
    return {"message": "Session reset", "agent_id": agent_id}

@app.get("/")
def root():
    return {
        "message": "Exercise Agent Platform API",
        "version": "2.0.0", 
        "endpoints": {
            "create_agent": "POST /create-agent - Agent owner creates agent",
            "end_user_chat": "POST /end-user/chat/{agent_id} - End user chats with agent", 
            "agent_owner_commands": "POST /agent-owner/chat/{agent_id} - Agent owner sends instructions",
            "agent_status": "GET /status/{agent_id} - Get agent status",
            "reset_agent": "POST /reset/{agent_id} - Reset agent session"
        },
        "terminology": {
            "agent_owner": "Person who creates and manages the agent",
            "end_user": "Person who interacts with the agent"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

