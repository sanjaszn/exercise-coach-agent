# app/tools.py
from app.memory import memory_store

def send_exercise_fn(user_id: str) -> str:
    """Send a new exercise to the user."""
    exercises = [
        "Do 10 push-ups",
        "Take a brisk 5-minute walk",
        "Do 10 lunges (5 each leg)"
    ]
    return exercises[0]  # Simplified for testing

def send_reminder_fn(user_id: str) -> str:
    """Send a reminder to the user."""
    session = memory_store.get(user_id) or {}
    exercise = session.get("last_exercise", "your exercise")
    reminders_sent = session.get("reminders_sent", 0)
    return f"Reminder {reminders_sent}/3: Don't forget to complete your exercise: {exercise}. Reply when done!"

def check_feedback_fn(user_id: str) -> str:
    """Check for user feedback."""
    session = memory_store.get(user_id) or {}
    feedback = session.get("feedback")
    if feedback:
        return feedback
    return "No feedback yet"