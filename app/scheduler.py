"""Optional APScheduler bootstrap for scheduled group messages."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler=AsyncIOScheduler(timezone="UTC")
def start_scheduler():
    if not scheduler.running: scheduler.start()
def stop_scheduler():
    if scheduler.running: scheduler.shutdown(wait=False)
