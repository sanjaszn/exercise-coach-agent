import requests
from app.memory import memory_store
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load .env
load_dotenv()

def fetch_agent_owner_instructions(user_id: str, agent_owner_id: str) -> dict:
    """Fetch agent owner instructions directly from ChromaDB."""
    logger.debug(f"Getting agent owner instructions for user_id={user_id}, agent_owner_id={agent_owner_id}")
    
    session = memory_store.get(user_id) or {}
    instruction = session.get("agent_owner_instruction", {
        "instruction_id": "default_123",
        "agent_owner_id": agent_owner_id,
        "user_id": user_id,
        "prompt": "Motivate the user to stay consistent.",
        "timestamp": datetime.now().isoformat()
    })
    
    logger.debug(f"Retrieved agent owner instruction: {instruction}")
    return instruction
   
def parse_agent_owner_prompt(prompt: str) -> dict:
    """Parse agent owner prompt to extract intent and details, and detect contradictions."""
    prompt = prompt.lower()
    result = {
        "motivation_type": "general",  # Default
        "include_goals": False,
        "warning_tone": False,
        "contradiction": False
    }
    
    positive_cues = ["motivate", "encourage", "inspire", "stay consistent", "push", "keep going"]
    negative_cues = ["give up", "be lazy", "quit", "rest instead", "don't try"]
    has_positive = any(word in prompt for word in positive_cues)
    has_negative = any(word in prompt for word in negative_cues)
    if has_positive and has_negative:
        result["contradiction"] = True
    if "goal" in prompt:
        result["motivation_type"] = "goal_reminder"
        result["include_goals"] = True
    if "warn" in prompt or "lack of exercise" in prompt:
        result["motivation_type"] = "warning"
        result["warning_tone"] = True
    
    logger.debug(f"Parsed prompt '{prompt}' to {result}")
    return result 