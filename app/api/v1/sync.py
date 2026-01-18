from fastapi import APIRouter, Depends, status, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.api.dependencies import get_current_trader
from app.db.session import get_db
from app.db.models import Trader, TraderStatus
from app.core.security import verify_token
from app.services.sync import sync_products_from_admin, sync_orders_from_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


async def get_trader_from_session_or_bearer(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Trader:
    # Try session token first
    token = request.session.get("access_token")

    # If no session token, try Bearer token from header
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    trader_id = int(payload["sub"])
    result = await db.execute(select(Trader).where(Trader.id == trader_id))
    trader = result.scalar_one_or_none()

    if not trader or trader.status != TraderStatus.ACTIVE:
        raise HTTPException(status_code=401, detail="Trader not active")

    return trader


@router.post("/products")
async def sync_products(
    request: Request,
    background_tasks: BackgroundTasks,
    trader: Trader = Depends(get_trader_from_session_or_bearer),
    db: AsyncSession = Depends(get_db),
):
    # Get backend access token from session
    backend_token = request.session.get("backend_access_token", "")

    logger.info(f"Sync products initiated by trader {trader.id}, backend token length: {len(backend_token)}")
    background_tasks.add_task(sync_products_from_admin, db, trader, backend_token)

    # Return HTML response for htmx
    html_response = """
    <div class="alert alert-success alert-dismissible fade show" role="alert">
        <i class="bi bi-check-circle"></i> Product sync initiated successfully! Products will be updated shortly.
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    """
    return HTMLResponse(content=html_response, status_code=200)


@router.post("/orders")
async def sync_orders(
    request: Request,
    background_tasks: BackgroundTasks,
    trader: Trader = Depends(get_trader_from_session_or_bearer),
    db: AsyncSession = Depends(get_db),
):
    # Get backend access token from session
    backend_token = request.session.get("backend_access_token", "")

    logger.info(f"Sync orders initiated by trader {trader.id}, backend token length: {len(backend_token)}")
    background_tasks.add_task(sync_orders_from_admin, db, trader, backend_token)

    # Return HTML response for htmx
    html_response = """
    <div class="alert alert-success alert-dismissible fade show" role="alert">
        <i class="bi bi-check-circle"></i> Order sync initiated successfully! Orders will be updated shortly.
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    """
    return HTMLResponse(content=html_response, status_code=200)
