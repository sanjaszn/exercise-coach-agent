# app/routing.py
from app.tools import should_send_exercise, should_send_reminder
from app.memory import memory_store

def route_input(user_input: str, user_id: str) -> str:
    """Enhanced routing that considers time and user state."""
    user_input = user_input.lower()
    
    # Handle explicit user requests first
    if "schedule" in user_input:
        return "schedule"
    elif "how" in user_input or "what" in user_input or "why" in user_input:
        return "question"
    elif "check feedback" in user_input:
        return "check_feedback"
    elif "send exercise" in user_input:
        return "send_exercise"
    
    # For automatic hourly runs (empty input), use time-based logic
    if not user_input and user_id:
        session = memory_store.get(user_id)
        
        # Priority 1: Send exercise if it's time
        if should_send_exercise(user_id):
            return "send_exercise"
            
        # Priority 2: Send reminder if needed
        if should_send_reminder(user_id):
            return "send_reminder"
            
        # Priority 3: Check feedback if exercise exists but no feedback
        if session.get("last_exercise") and not session.get("feedback"):
            return "check_feedback"
    
    # Default fallback
    return "send_exercise"