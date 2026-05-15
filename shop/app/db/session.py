from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

AsyncSessionLocal = async_session


async def get_db():
    """Dependency for getting async database session."""
    async with async_session() as session:
        yield session


async def get_local_trader_id(db: AsyncSession) -> int:
    from app.db.models import Trader
    result = await db.execute(select(Trader.id).limit(1))
    trader_id = result.scalar_one_or_none()
    if trader_id is None:
        raise RuntimeError("No trader found in database")
    return trader_id
