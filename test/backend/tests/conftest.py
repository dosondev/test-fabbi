import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use SQLite for tests before app modules initialize their default engine.
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.api.deps import get_redis
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

TEST_REDIS = MagicMock()
TEST_REDIS.get = AsyncMock(return_value=None)
TEST_REDIS.set = AsyncMock()
TEST_REDIS.delete = AsyncMock()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def override_get_redis():
    return TEST_REDIS


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis] = override_get_redis


@pytest.fixture
def redis_mock():
    TEST_REDIS.reset_mock()
    TEST_REDIS.get = AsyncMock(return_value=None)
    TEST_REDIS.set = AsyncMock()
    TEST_REDIS.delete = AsyncMock()
    return TEST_REDIS


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_maker() as session:
        yield session


@pytest.fixture
def auth_headers() -> dict:
    """Create auth headers with a valid token for testing."""
    token = create_access_token(data={"sub": "00000000-0000-0000-0000-000000000001"})
    return {"Authorization": f"Bearer {token}"}
