import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Trader, TraderStatus, AuditLog
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.core.admin_client import admin_client

logger = logging.getLogger(__name__)


async def register_trader(db: AsyncSession, data: RegisterRequest) -> Trader:
    logger.info(f"Starting trader registration for email: {data.email}")

    result = await db.execute(select(Trader).where(Trader.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        logger.warning(f"Registration attempt with existing email: {data.email}")
        raise ValueError("Email already registered")

    logger.info(f"Creating local trader account for: {data.email}")
    trader = Trader(
        email=data.email,
        password_hash=hash_password(data.password),
        business_name=data.business_name,
        status=TraderStatus.PENDING
    )
    db.add(trader)
    await db.flush()
    logger.info(f"Local trader account created with id: {trader.id}")

    logger.info(f"Calling backend registration for: {data.email}")
    try:
        backend_response = await admin_client.register_trader(data.email, data.business_name, data.password)
        logger.info(f"Backend registration successful for {data.email}: {backend_response}")

        if backend_response.get("user") and backend_response["user"].get("id"):
            trader.backend_user_id = backend_response["user"]["id"]
            logger.info(f"Stored backend_user_id: {trader.backend_user_id} for trader {trader.id}")
    except Exception as e:
        logger.error(f"Backend registration failed for {data.email}: {str(e)}")

    audit_log = AuditLog(
        trader_id=trader.id,
        action="REGISTER",
        entity="trader",
        entity_id=trader.id,
        audit_data={"email": data.email, "business_name": data.business_name}
    )
    db.add(audit_log)
    await db.commit()
    logger.info(f"Registration completed and committed to database for: {data.email}")
    await db.refresh(trader)

    return trader


async def login(db: AsyncSession, email: str, password: str) -> TokenResponse:
    result = await db.execute(select(Trader).where(Trader.email == email))
    trader = result.scalar_one_or_none()

    if not trader:
        raise ValueError("Invalid credentials")

    if trader.status != TraderStatus.ACTIVE:
        raise ValueError("Trader account not yet approved")

    if not verify_password(password, trader.password_hash):
        raise ValueError("Invalid credentials")

    access_token = create_access_token({"sub": str(trader.id), "email": trader.email})
    refresh_token = create_refresh_token({"sub": str(trader.id)})

    audit_log = AuditLog(
        trader_id=trader.id,
        action="LOGIN",
        entity="trader",
        entity_id=trader.id,
        audit_data={"email": email}
    )
    db.add(audit_log)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role="TRADER",
        user_id=trader.id
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    from app.core.security import verify_token

    payload = verify_token(refresh_token)
    if not payload or "sub" not in payload:
        raise ValueError("Invalid refresh token")

    trader_id = int(payload["sub"])
    result = await db.execute(select(Trader).where(Trader.id == trader_id))
    trader = result.scalar_one_or_none()

    if not trader or trader.status != TraderStatus.ACTIVE:
        raise ValueError("Trader not found or not active")

    access_token = create_access_token({"sub": str(trader.id), "email": trader.email})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role="TRADER",
        user_id=trader.id
    )
