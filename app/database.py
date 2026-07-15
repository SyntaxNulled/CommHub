import os
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session_factory() as session:
        yield session


async def init_db():
    os.makedirs(settings.data_dir, exist_ok=True)
    async with engine.begin() as conn:
        from app.models import EmailAccount, Email, CalendarEvent, Folder, AutomationRule, AIProviderConfig  # noqa
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(sqlalchemy.text("ALTER TABLE calendar_events ADD COLUMN rrule VARCHAR(512)"))
        except Exception:
            pass

        for col in ["snoozed_until", "send_at"]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE emails ADD COLUMN {col} DATETIME"))
            except Exception:
                pass

    await _ensure_system_folders()


async def _ensure_system_folders():
    """Ensure the four system mail folders exist. Idempotent."""
    from sqlalchemy import select
    from app.models import Folder

    system_folders = [
        ("INBOX", "blue", "inbox", 0),
        ("SENT", "gray", "sent", 1),
        ("DRAFTS", "gray", "draft", 2),
        ("STARRED", "amber", "star", 3),
    ]
    async with async_session_factory() as session:
        for name, color, icon, order in system_folders:
            existing = await session.execute(
                select(Folder).where(Folder.normalized_name == name.upper())
            )
            if existing.scalar_one_or_none() is None:
                session.add(Folder(
                    name=name, normalized_name=name.upper(),
                    color=color, icon=icon, is_system=True, sort_order=order,
                ))
        await session.commit()
