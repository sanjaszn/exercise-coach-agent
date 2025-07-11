from langchain.tools import Tool
from memory import memory_store
from typing import Any
import random

EXERCISES = [
    "Do 10 push-ups!",
    "Take a brisk 5-minute walk.",
    "Try 1 minute of deep breathing.",
    "Do 15 squats!",
    "Stretch your arms and back for 2 minutes."
]

def send_exercise_fn(user_id: str) -> str:
    print(f"Sending exercise to user called {user_id}")
    exercise = random.choice(EXERCISES)
    memory_store.update(user_id, {"last_exercise": exercise, "feedback": None, "reminders_sent": 0})
    return f"Here's your daily exercise: {exercise} Let me know when you're done!"

def check_feedback_fn(user_id: str) -> str:
    session = memory_store.get(user_id)
    feedback = session.get("feedback")
    if feedback:
        return f"Thanks for your feedback: '{feedback}'. Great job!"
    else:
        return "I'm still waiting for your feedback. Let me know when you've completed the exercise!"

def send_reminder_fn(user_id: str) -> str:
    session = memory_store.get(user_id)
    reminders = session.get("reminders_sent", 0)
    if session.get("feedback"):
        return "No reminder needed. Feedback already received."
    if reminders >= 3:
        return "Maximum reminders sent. I'll wait for your feedback."
    reminders += 1
    memory_store.update(user_id, {"reminders_sent": reminders})
    return f"Reminder {reminders}: Don't forget to complete your exercise! Reply when done."

send_exercise = Tool(
    name="send_exercise",
    func=send_exercise_fn,
    description="Send a daily exercise to the user."
)

check_feedback = Tool(
    name="check_feedback",
    func=check_feedback_fn,
    description="Check if the user has provided feedback."
)

send_reminder = Tool(
    name="send_reminder",
    func=send_reminder_fn,
    description="Send a reminder to the user if feedback is missing."
)

tools = [send_exercise, check_feedback, send_reminder] 