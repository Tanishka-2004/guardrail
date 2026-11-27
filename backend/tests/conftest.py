import pytest
import asyncio
import os
import sys
from typing import AsyncGenerator
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure backend root is on sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.database import Base, get_db
from app.models.analyst import Analyst
from app.core.security import get_password_hash, create_access_token
from app.domain.enums import UserRole
from app.main import app as fastapi_app

# In-memory SQLite async test database
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

@pytest.fixture(autouse=True)
def setup_test_db():
    async def _init():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_init())
    yield
    async def _cleanup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.run(_cleanup())

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

fastapi_app.dependency_overrides[get_db] = override_get_db

# Patch background consumers and workers to use test session factory
import app.kafka.consumer as kafka_consumer_mod
import app.workers.stale_claim_reaper as reaper_mod
import app.workers.sla_escalation_worker as sla_worker_mod
import app.workers.outbox_publisher as outbox_mod
import app.workers.dlq_auto_replay as dlq_replay_mod

kafka_consumer_mod.AsyncSessionLocal = TestSessionLocal
reaper_mod.AsyncSessionLocal = TestSessionLocal
sla_worker_mod.AsyncSessionLocal = TestSessionLocal
outbox_mod.AsyncSessionLocal = TestSessionLocal
dlq_replay_mod.AsyncSessionLocal = TestSessionLocal

@pytest.fixture
async def seed_analysts(db_session: AsyncSession):
    analyst_user = Analyst(
        id="usr_analyst_01",
        name="Sarah Chen",
        email="analyst@guardrail.io",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.ANALYST.value,
        team="Realtime Triage",
        workload_limit=10,
        is_active=True,
    )
    senior_user = Analyst(
        id="usr_senior_01",
        name="Elena Rostova",
        email="senior@guardrail.io",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.SENIOR_ANALYST.value,
        team="Escalations",
        workload_limit=12,
        is_active=True,
    )
    supervisor_user = Analyst(
        id="usr_supervisor_01",
        name="Marcus Vance",
        email="supervisor@guardrail.io",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.SUPERVISOR.value,
        team="Management",
        workload_limit=15,
        is_active=True,
    )
    admin_user = Analyst(
        id="usr_admin_01",
        name="Admin User",
        email="admin@guardrail.io",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.ADMIN.value,
        team="SecOps",
        workload_limit=20,
        is_active=True,
    )

    db_session.add_all([analyst_user, senior_user, supervisor_user, admin_user])
    await db_session.commit()

    return {
        "analyst": analyst_user,
        "senior": senior_user,
        "supervisor": supervisor_user,
        "admin": admin_user,
    }

@pytest.fixture
def auth_headers(seed_analysts):
    def _get_headers(role: str = "ANALYST"):
        user = seed_analysts[role.lower().replace("_analyst", "")]
        token = create_access_token({
            "sub": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "team": user.team,
        })
        return {"Authorization": f"Bearer {token}"}
    return _get_headers

@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield client
