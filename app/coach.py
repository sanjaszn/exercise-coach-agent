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
    """Fetch coach instructions from API and cache them."""
    session = memory_store.get(user_id) or {}
    last_fetched = session.get("last_instruction_fetch")
    now = datetime.now()
    
    # Fetch only if not fetched in the last hour
    if not last_fetched or (now - datetime.fromisoformat(last_fetched)).total_seconds() > 3600:
        try:
            logger.debug(f"Fetching instructions for user_id={user_id}, coach_id={coach_id}")
            response = requests.get(
                f"https://api.myagents.ai/coach-commands?user_id={user_id}&coach_id={coach_id}",
                headers={"Authorization": f"Bearer {os.getenv('API_TOKEN')}"}
            )
            response.raise_for_status()
            instruction = response.json()
            logger.debug(f"Fetched instruction: {instruction}")
            memory_store.update(user_id, {
                "coach_instruction": instruction,
                "last_instruction_fetch": now.isoformat()
            })
            return instruction
        except requests.RequestException as e:
            logger.debug(f"API request failed: {e}")
            # Fallback to cached instruction or default
            return session.get("coach_instruction", {"prompt": "Motivate the user to stay consistent."})
    logger.debug(f"Using cached instruction: {session.get('coach_instruction')}")
    return session.get("coach_instruction", {"prompt": "Motivate the user to stay consistent."})

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