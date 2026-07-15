import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base, get_db
from app.models import Folder
from app.main import app


TEST_DATABASE_URL = "sqlite+aiosqlite://"


async def _ensure_system_folders(session):
    from sqlalchemy import select

    system_folders = [
        ("INBOX", "blue", "inbox", 0),
        ("SENT", "gray", "sent", 1),
        ("DRAFTS", "gray", "draft", 2),
        ("STARRED", "amber", "star", 3),
    ]
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


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await _ensure_system_folders(session)
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
