from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_trader
from app.db.session import get_db
from app.db.models import Trader
from app.schemas.category import CategoryResponse
from app.services.category import list_categories


router = APIRouter(prefix="/api/v1/trader", tags=["categories"])


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(
    trader: Trader = Depends(get_current_trader),
    db: AsyncSession = Depends(get_db)
):
    categories = await list_categories(db)
    return categories
