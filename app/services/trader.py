from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.db.models import Trader, AuditLog
from app.schemas.trader import TraderProfileResponse, TraderProfileUpdate


async def get_trader_profile(db: AsyncSession, trader_id: int) -> TraderProfileResponse:
    result = await db.execute(select(Trader).where(Trader.id == trader_id))
    trader = result.scalar_one_or_none()

    if not trader:
        raise ValueError("Trader not found")

    return TraderProfileResponse(
        id=trader.id,
        email=trader.email,
        business_name=trader.business_name,
        backend_user_id=trader.backend_user_id,
        api_key=trader.api_key,
        status=trader.status.value,
        created_at=trader.created_at,
        updated_at=trader.updated_at
    )


async def update_trader_profile(
    db: AsyncSession,
    trader_id: int,
    data: TraderProfileUpdate
) -> TraderProfileResponse:
    result = await db.execute(select(Trader).where(Trader.id == trader_id))
    trader = result.scalar_one_or_none()

    if not trader:
        raise ValueError("Trader not found")

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is not None:
            setattr(trader, field, value)

    trader.updated_at = datetime.utcnow()

    audit_log = AuditLog(
        trader_id=trader_id,
        action="PROFILE_UPDATE",
        entity="trader",
        entity_id=trader_id,
        audit_data=update_data
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(trader)

    return TraderProfileResponse(
        id=trader.id,
        email=trader.email,
        business_name=trader.business_name,
        backend_user_id=trader.backend_user_id,
        api_key=trader.api_key,
        status=trader.status.value,
        created_at=trader.created_at,
        updated_at=trader.updated_at
    )
