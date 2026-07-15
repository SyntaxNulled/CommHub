import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db, init_db, async_session_factory
from app.models import AutomationRule
from app.routers import health, ai, automation, emails, calendar
from app.automation.scheduler import start_scheduler, stop_scheduler, add_cron_job
from app.automation.engine import execute_cron_rule
from app.mock_data import seed_demo_data as _seed_demo_data

logger = logging.getLogger(__name__)


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
            try:
                add_cron_job(execute_cron_rule, rule.id, rule.cron_schedule)
            except ValueError as exc:
                # A bad cron string must never prevent the app from booting
                logger.warning(f"Skipping rule {rule.id} ('{rule.name}') — invalid cron '{rule.cron_schedule}': {exc}")

    yield
    await stop_scheduler()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.include_router(health.router)
app.include_router(ai.router)
app.include_router(automation.router)
app.include_router(emails.router)
app.include_router(calendar.router)


@app.post("/api/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    return await _seed_demo_data(db)


if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
    static_dir = base / "app" / "static"
else:
    static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
