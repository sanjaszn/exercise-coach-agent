# app/routing.py
def route_input(user_input: str) -> str:
    """Route user input to the appropriate intent."""
    user_input = user_input.lower()
    if "schedule" in user_input:
        return "schedule"
    elif "how" in user_input or "what" in user_input or "why" in user_input:
        return "question"
    elif "check feedback" in user_input:
        return "check_feedback"
    elif "send exercise" in user_input:
        return "send_exercise"
    elif "check status" in user_input:
        return "send_reminder"
    return "send_exercise"  # Default