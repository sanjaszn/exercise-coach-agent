from app.memory import memory_store
from datetime import datetime, timedelta
import random
from app.coach import fetch_coach_instructions, parse_coach_prompt

EXERCISES = [
    "Do 10 push-ups",
    "Take a 5-minute walk", 
    "Do 15 squats",
    "Hold a plank for 30 seconds",
    "Do 10 lunges (5 each leg)",
    "Try 1 minute of deep breathing"
]

def should_send_exercise(user_id: str) -> bool:
    """Check if it's time to send exercise to user."""
    session = memory_store.get(user_id) or {}
    if not session.get("scheduled_hour"):
        return False
        
    now = datetime.now()
    scheduled_hour = session.get("scheduled_hour")
    scheduled_minute = session.get("scheduled_minute", 0)
    
    # Check if it's the right time and no exercise sent today
    if (now.hour == scheduled_hour and 
        abs(now.minute - scheduled_minute) <= 30):  # 30-minute window
        
        last_exercise_date = session.get("last_exercise_date")
        today = now.date().isoformat()
        
        if last_exercise_date != today:
            return True
    
    return False

def should_send_reminder(user_id: str) -> bool:
    """Check if we should send a reminder."""
    session = memory_store.get(user_id) or {}
    
    if not session.get("last_exercise") or session.get("feedback"):
        return False
    
    # Check warning condition first
    instruction = fetch_coach_instructions(user_id, "coach_001")  # Consistent coach_id
    parsed_instruction = parse_coach_prompt(instruction.get("prompt", ""))
    if parsed_instruction["warning_tone"] and session.get("last_exercise_date") and session.get("reminders_sent", 0) < 3:
        try:
            days_since = (datetime.now().date() - datetime.fromisoformat(session["last_exercise_date"]).date()).days
            if days_since >= 3:
                return True
        except ValueError:
            pass
    
    # Fallback to time-based reminder logic
    exercise_time_str = session.get("exercise_sent_at")
    if not exercise_time_str:
        return False
        
    exercise_time = datetime.fromisoformat(exercise_time_str)
    hours_since = (datetime.now() - exercise_time).total_seconds() / 3600
    reminders_sent = session.get("reminders_sent", 0)
    
    # Send reminders at 2h, 4h, 6h after exercise
    if (hours_since >= 2 and reminders_sent == 0) or \
       (hours_since >= 4 and reminders_sent == 1) or \
       (hours_since >= 6 and reminders_sent == 2):
        return True
        
    return False

def send_exercise_fn(user_id: str) -> str:
    """Send a new exercise to the user."""
    exercise = random.choice(EXERCISES)
    now = datetime.now()
    
    memory_store.update(user_id, {
        "last_exercise": exercise,
        "feedback": None,
        "reminders_sent": 0,
        "exercise_sent_at": now.isoformat(),
        "last_exercise_date": now.date().isoformat()
    })
    
    return EXERCISES[0]  # TODO: Remove this; just for testing

def send_reminder_fn(user_id: str) -> str:
    """Send a reminder to the user."""
    session = memory_store.get(user_id) or {}
    exercise = session.get("last_exercise", "your exercise")
    reminders_sent = session.get("reminders_sent", 0)
    
    memory_store.update(user_id, {"reminders_sent": reminders_sent + 1})
    
    return f"Reminder {reminders_sent + 1}/3: Don't forget to complete: {exercise}"

def check_feedback_fn(user_id: str) -> str:
    """Check for user feedback."""
    session = memory_store.get(user_id) or {}
    feedback = session.get("feedback")
    
    if feedback:
        return feedback
    return "No feedback yet"

def schedule_session_fn(user_id: str, time_str: str) -> str:
    """Schedule a workout session."""
    from app.scheduler import set_user_schedule
    set_user_schedule(time_str)
    return f"Scheduled for {time_str} daily"