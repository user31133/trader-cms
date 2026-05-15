"""Creates a test trader with a known password so Playwright tests can log in."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.db.models import Trader, TraderStatus
from app.core.security import hash_password

DATABASE_URL = os.environ["DATABASE_URL"]
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "testpassword123"


async def seed():
    engine = create_async_engine(DATABASE_URL)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        result = await db.execute(select(Trader).where(Trader.email == TEST_EMAIL))
        if result.scalar_one_or_none():
            print(f"Test trader {TEST_EMAIL!r} already exists, skipping")
            return

        trader = Trader(
            email=TEST_EMAIL,
            password_hash=hash_password(TEST_PASSWORD),
            business_name="Test Shop",
            status=TraderStatus.ACTIVE,
            api_key="test-api-key-12345",
            backend_user_id=1,
        )
        db.add(trader)
        await db.commit()
        print(f"Created test trader: {TEST_EMAIL}")

    await engine.dispose()


asyncio.run(seed())
