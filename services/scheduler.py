import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from config import settings
from database.queries import get_due_reminders, mark_reminder_sent

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")

async def _process_reminders(bot):
    due = await get_due_reminders(datetime.utcnow())
    for reminder_id, user_id, message in due:
        try:
            await bot.send_message(user_id, f"Reminder: {message}")
            await mark_reminder_sent(reminder_id)
        except Exception as e:
            logger.error(f"Failed to send reminder {reminder_id}: {e}")

async def _health_check(bot):
    if not settings.HEALTH_CHECK_URL:
        return
    from .health_monitor import health_monitor
    is_healthy = await health_monitor.check(settings.HEALTH_CHECK_URL)
    if not is_healthy:
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(admin_id, "Alert: Service health check failed.")
            except Exception:
                pass

async def _cleanup_temp():
    import glob, os
    from pathlib import Path
    temp_dir = Path("storage/temp")
    if temp_dir.exists():
        for f in glob.glob(str(temp_dir / "*.tmp")):
            try: os.remove(f)
            except OSError: pass

def init_scheduler(bot):
    scheduler.add_job(_process_reminders, IntervalTrigger(minutes=5), args=[bot], id="reminders", replace_existing=True)
    if settings.HEALTH_CHECK_URL:
        scheduler.add_job(_health_check, CronTrigger(minute="*/10"), args=[bot], id="health_check", replace_existing=True)
    scheduler.add_job(_cleanup_temp, CronTrigger(hour=3, minute=0), id="cleanup", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler initialized")