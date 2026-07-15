import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


os.makedirs(settings.data_dir, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        from app.models import EmailAccount, Email, CalendarEvent, AutomationRule  # noqa
        await conn.run_sync(Base.metadata.create_all)
