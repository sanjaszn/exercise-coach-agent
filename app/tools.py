from langchain.tools import Tool
from memory import memory_store
from typing import Any
import random
from datetime import datetime

EXERCISES = [
    "Do 10 push-ups!",
    "Take a brisk 5-minute walk.",
    "Try 1 minute of deep breathing.",
    "Do 15 squats!",
    "Stretch your arms and back for 2 minutes.",
    "Do 20 jumping jacks!",
    "Hold a plank for 30 seconds.",
    "Do 10 lunges (5 each leg)."
]

def send_exercise_fn(user_id: str) -> str:
    """Send a new exercise to the user."""
    print(f"Sending exercise to user {user_id}")
    
    # Check if user already has an unfinished exercise
    session = memory_store.get(user_id)
    if session.get("last_exercise") and not session.get("feedback"):
        return f"You still have an unfinished exercise: {session['last_exercise']} Please complete it first!"
    
    exercise = random.choice(EXERCISES)
    memory_store.update(user_id, {
        "last_exercise": exercise, 
        "feedback": None, 
        "reminders_sent": 0,
        "exercise_sent_at": datetime.now().isoformat()
    })
    
    return f"Here's your daily exercise: {exercise} Let me know when you're done!"

def check_feedback_fn(user_id: str) -> str:
    """Check if the user has provided feedback."""
    session = memory_store.get(user_id)
    
    if not session.get("last_exercise"):
        return "No exercise has been sent yet. Let me send you one!"
    
    feedback = session.get("feedback")
    if feedback:
        return f"Thanks for your feedback: '{feedback}'. Great job completing your exercise!"
    else:
        reminders = session.get("reminders_sent", 0)
        if reminders >= 3:
            return "I've sent you 3 reminders already. I'm still waiting for your feedback on the exercise. Please let me know when you complete it!"
        else:
            return "I'm still waiting for your feedback. Let me know when you've completed the exercise!"

def send_reminder_fn(user_id: str) -> str:
    """Send a reminder to the user."""
    session = memory_store.get(user_id)
    
    # Check if feedback already received
    if session.get("feedback"):
        return "No reminder needed - you've already completed the exercise!"
    
    # Check if exercise was sent
    if not session.get("last_exercise"):
        return "No exercise to remind about. Let me send you one first!"
    
    reminders = session.get("reminders_sent", 0)
    if reminders >= 3:
        return "Maximum reminders sent. I'll wait for your feedback."
    
    reminders += 1
    memory_store.update(user_id, {"reminders_sent": reminders})
    
    exercise = session.get("last_exercise")
    return f"Reminder {reminders}/3: Don't forget to complete your exercise: {exercise} Reply when done!"

# Create tools with better descriptions for ReAct reasoning
send_exercise = Tool(
    name="send_exercise",
    func=send_exercise_fn,
    description="Send a new daily exercise to the user. Use this when the user has no current exercise or has completed their previous exercise."
)

check_feedback = Tool(
    name="check_feedback",
    func=check_feedback_fn,
    description="Check if the user has provided feedback on their exercise. Use this to see the current status of the user's exercise completion."
)

send_reminder = Tool(
    name="send_reminder",
    func=send_reminder_fn,
    description="Send a reminder to the user about their incomplete exercise. Use this when the user has an exercise but no feedback, and hasn't received maximum reminders yet."
)

tools = [send_exercise, check_feedback, send_reminder]