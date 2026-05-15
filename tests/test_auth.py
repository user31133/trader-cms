import pytest
from sqlalchemy import select

from app.db.models import Trader, TraderStatus
from app.services.auth import register_trader, login
from app.schemas.auth import RegisterRequest
from app.core.security import verify_password


@pytest.mark.asyncio
async def test_register_trader(db_session):
    data = RegisterRequest(
        email="newtrader@example.com",
        password="secure_password_123",
        business_name="New Shop"
    )

    trader = await register_trader(db_session, data)

    assert trader.email == "newtrader@example.com"
    assert trader.business_name == "New Shop"
    assert trader.status == TraderStatus.PENDING
    assert verify_password("secure_password_123", trader.password_hash)


@pytest.mark.asyncio
async def test_register_duplicate_email(db_session, active_trader):
    data = RegisterRequest(
        email=active_trader.email,
        password="another_password_123",
        business_name="Another Shop"
    )

    with pytest.raises(ValueError):
        await register_trader(db_session, data)


@pytest.mark.asyncio
async def test_login_success(db_session, active_trader):
    from app.services.auth import login

    token_response = await login(db_session, "test@example.com", "password")

    assert token_response.access_token
    assert token_response.refresh_token
    assert token_response.user_id == active_trader.id
    assert token_response.role == "TRADER"


@pytest.mark.asyncio
async def test_login_pending_trader(db_session):
    pending_trader = Trader(
        email="pending@example.com",
        password_hash="$2b$12$hashed_password",
        business_name="Pending Shop",
        status=TraderStatus.PENDING
    )
    db_session.add(pending_trader)
    await db_session.commit()

    with pytest.raises(ValueError, match="not yet approved"):
        await login(db_session, "pending@example.com", "password")


@pytest.mark.asyncio
async def test_login_invalid_password(db_session, active_trader):
    with pytest.raises(ValueError, match="Invalid credentials"):
        await login(db_session, "test@example.com", "wrong_password")
