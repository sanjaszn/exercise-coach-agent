from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from agent_runner import run_agent_session
from memory import memory_store
import threading

scheduler = BackgroundScheduler()
scheduler.start()

job_refs = {}
lock = threading.Lock()

def schedule_user_job(user_id: str, time_str: str):
    hour, minute = map(int, time_str.split(":"))
    def job():
        run_agent_session(user_id)
    with lock:
        if user_id in job_refs:
            job_refs[user_id].remove()
        job_refs[user_id] = scheduler.add_job(
            job,
            CronTrigger(hour=hour, minute=minute),
            id=f"exercise_{user_id}",
            replace_existing=True
        )
    memory_store.update(user_id, {"scheduled_time": time_str})

def cancel_user_job(user_id: str):
    with lock:
        if user_id in job_refs:
            job_refs[user_id].remove()
            del job_refs[user_id]
    memory_store.update(user_id, {"scheduled_time": None})

def run_now(user_id: str):
    return run_agent_session(user_id) 