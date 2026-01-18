from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_trader
from app.db.session import get_db
from app.db.models import Trader
from app.schemas.order import OrderResponse, OrderStats
from app.services.order import get_trader_orders, get_trader_stats


router = APIRouter(prefix="/api/v1/trader", tags=["orders"])


@router.get("/orders", response_model=dict)
async def list_orders(
    page: int = 1,
    limit: int = 10,
    trader: Trader = Depends(get_current_trader),
    db: AsyncSession = Depends(get_db)
):
    try:
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10

        orders, total_count = await get_trader_orders(db, trader.id, page, limit)
        total_pages = (total_count + limit - 1) // limit

        return {
            "items": orders,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/stats", response_model=OrderStats)
async def get_stats(
    trader: Trader = Depends(get_current_trader),
    db: AsyncSession = Depends(get_db)
):
    try:
        stats = await get_trader_stats(db, trader.id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
