from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_trader
from app.db.session import get_db
from app.db.models import Trader
from app.schemas.trader import TraderProfileResponse, TraderProfileUpdate
from app.services.trader import get_trader_profile, update_trader_profile


router = APIRouter(prefix="/api/v1/trader", tags=["profile"])


@router.get("/profile", response_model=TraderProfileResponse)
async def get_profile(
    trader: Trader = Depends(get_current_trader),
    db: AsyncSession = Depends(get_db)
):
    profile = await get_trader_profile(db, trader.id)
    return profile


@router.patch("/profile", response_model=TraderProfileResponse)
async def update_profile(
    data: TraderProfileUpdate,
    trader: Trader = Depends(get_current_trader),
    db: AsyncSession = Depends(get_db)
):
    if not data.model_dump(exclude_unset=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    updated = await update_trader_profile(db, trader.id, data)
    return updated
