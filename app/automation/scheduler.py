import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()})


async def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")


async def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


def add_cron_job(func, rule_id: int, cron_expression: str):
    trigger = CronTrigger.from_crontab(cron_expression)
    scheduler.add_job(
        func,
        trigger=trigger,
        id=f"rule_{rule_id}",
        name=f"rule_{rule_id}",
        replace_existing=True,
        args=[rule_id],
    )
    logger.info(f"Scheduled rule {rule_id} with cron '{cron_expression}'")


def remove_job(rule_id: int):
    job_id = f"rule_{rule_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed scheduled job for rule {rule_id}")


def get_scheduled_jobs() -> list[dict]:
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
    ]
