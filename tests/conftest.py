import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db.base import Base
from app.db.models import Trader, TraderStatus, AuditLog


DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine():
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def active_trader(db_session):
    trader = Trader(
        email="test@example.com",
        password_hash="$2b$12$hashed_password",
        business_name="Test Shop",
        status=TraderStatus.ACTIVE,
        api_key="test_api_key_123"
    )
    db_session.add(trader)
    await db_session.commit()
    await db_session.refresh(trader)
    return trader
