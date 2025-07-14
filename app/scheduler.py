from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from agent_runner import run_agent_session
from memory import memory_store
import threading
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()
scheduler.start()

job_refs = {}
reminder_jobs = {}
lock = threading.Lock()

def schedule_user_job(user_id: str, time_str: str):
    """Schedule daily exercise for user."""
    hour, minute = map(int, time_str.split(":"))
    
    def exercise_job():
        print(f"Running scheduled exercise for user {user_id}")
        response = run_agent_session(user_id)
        print(f"Exercise response: {response}")
        
        # Schedule reminder jobs if exercise was sent
        session = memory_store.get(user_id)
        if session.get("last_exercise") and not session.get("feedback"):
            schedule_reminder_jobs(user_id)
    
    with lock:
        # Cancel existing jobs
        if user_id in job_refs:
            job_refs[user_id].remove()
        
        # Schedule new exercise job
        job_refs[user_id] = scheduler.add_job(
            exercise_job,
            CronTrigger(hour=hour, minute=minute),
            id=f"exercise_{user_id}",
            replace_existing=True
        )
    
    memory_store.update(user_id, {"scheduled_time": time_str})

def schedule_reminder_jobs(user_id: str):
    """Schedule automatic reminders for user."""
    def create_reminder_job(reminder_num):
        def reminder_job():
            session = memory_store.get(user_id)
            if session.get("feedback"):
                # User already provided feedback, cancel remaining reminders
                cancel_reminder_jobs(user_id)
                return
            
            reminders_sent = session.get("reminders_sent", 0)
            if reminders_sent >= 3:
                print(f"Maximum reminders sent for user {user_id}")
                cancel_reminder_jobs(user_id)
                return
            
            print(f"Sending reminder {reminders_sent + 1} to user {user_id}")
            response = run_agent_session(user_id)
            print(f"Reminder response: {response}")
        
        return reminder_job
    
    with lock:
        # Cancel existing reminder jobs
        cancel_reminder_jobs(user_id)
        
        # Schedule 3 reminders: after 2 hours, 4 hours, and 6 hours
        reminder_times = [2, 4, 6]  # hours after exercise
        reminder_jobs[user_id] = []
        
        for i, hours in enumerate(reminder_times):
            run_time = datetime.now() + timedelta(hours=hours)
            job = scheduler.add_job(
                create_reminder_job(i + 1),
                DateTrigger(run_date=run_time),  # Use DateTrigger for one-time execution
                id=f"reminder_{user_id}_{i}",
                replace_existing=True
            )
            reminder_jobs[user_id].append(job)
            print(f"Scheduled reminder {i + 1} for user {user_id} at {run_time}")

def cancel_reminder_jobs(user_id: str):
    """Cancel all reminder jobs for user."""
    with lock:
        if user_id in reminder_jobs:
            for job in reminder_jobs[user_id]:
                try:
                    job.remove()
                except:
                    pass  # Job might already be removed
            del reminder_jobs[user_id]
            print(f"Cancelled all reminder jobs for user {user_id}")

def cancel_user_job(user_id: str):
    """Cancel all jobs for user."""
    with lock:
        if user_id in job_refs:
            job_refs[user_id].remove()
            del job_refs[user_id]
    
    cancel_reminder_jobs(user_id)
    memory_store.update(user_id, {"scheduled_time": None})

def run_now(user_id: str):
    """Run agent session immediately."""
    response = run_agent_session(user_id)
    
    # If exercise was sent, schedule reminders
    session = memory_store.get(user_id)
    if session.get("last_exercise") and not session.get("feedback"):
        schedule_reminder_jobs(user_id)
    
    return response

def handle_feedback_received(user_id: str):
    """Call this when feedback is received to cancel reminders."""
    cancel_reminder_jobs(user_id)
    print(f"Feedback received for user {user_id}, cancelled remaining reminders")