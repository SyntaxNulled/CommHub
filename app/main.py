import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from app.config import settings
from app.database import init_db, async_session_factory
from app.models import AutomationRule
from app.routers import health, ai, automation, emails, calendar
from app.automation.scheduler import start_scheduler, stop_scheduler, add_cron_job
from app.automation.engine import execute_cron_rule


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_scheduler()

    async with async_session_factory() as session:
        result = await session.execute(
            select(AutomationRule).where(
                AutomationRule.is_enabled == True,
                AutomationRule.trigger_type == "cron_schedule",
                AutomationRule.cron_schedule.isnot(None),
            )
        )
        for rule in result.scalars().all():
            add_cron_job(execute_cron_rule, rule.id, rule.cron_schedule)

    yield
    await stop_scheduler()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.include_router(health.router)
app.include_router(ai.router)
app.include_router(automation.router)
app.include_router(emails.router)
app.include_router(calendar.router)


@app.post("/api/seed")
async def seed_demo_data():
    from app.mock_data import seed_demo_data as _seed
    return await _seed()


if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
    static_dir = base / "app" / "static"
else:
    static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
