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

def fetch_coach_instructions(user_id: str, coach_id: str) -> dict:
    """Fetch coach instructions directly from ChromaDB."""
    logger.debug(f"Getting coach instructions for user_id={user_id}, coach_id={coach_id}")
    
    session = memory_store.get(user_id) or {}
    instruction = session.get("coach_instruction", {
        "instruction_id": "default_123",
        "coach_id": coach_id,
        "user_id": user_id,
        "prompt": "Motivate the user to stay consistent.",
        "timestamp": datetime.now().isoformat()
    })
    
    logger.debug(f"Retrieved coach instruction: {instruction}")
    return instruction
   
def parse_coach_prompt(prompt: str) -> dict:
    """Parse coach prompt to extract intent and details."""
    prompt = prompt.lower()
    result = {
        "motivation_type": "general",  # Default
        "include_goals": False,
        "warning_tone": False
    }
    
    if "goal" in prompt:
        result["motivation_type"] = "goal_reminder"
        result["include_goals"] = True
    if "warn" in prompt or "lack of exercise" in prompt:
        result["motivation_type"] = "warning"
        result["warning_tone"] = True
    
    logger.debug(f"Parsed prompt '{prompt}' to {result}")
    return result