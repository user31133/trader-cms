from fastapi import APIRouter, Depends, status, Request, HTTPException
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
    trader: Trader = Depends(get_trader_from_session_or_bearer),
    db: AsyncSession = Depends(get_db),
):
    # Get backend tokens from session
    backend_token = request.session.get("backend_access_token", "")
    backend_refresh_token = request.session.get("backend_refresh_token", "")

    # Validate backend token exists
    if not backend_token:
        logger.warning(f"Sync products failed - no backend token for trader {trader.id}")
        html_response = """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="bi bi-exclamation-circle"></i> Session expired. Please logout and login again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
        return HTMLResponse(content=html_response, status_code=401)

    logger.info(f"Sync products initiated by trader {trader.id}")

    try:
        # Sync products with auto token refresh
        result, new_access, new_refresh = await sync_products_from_admin(
            db, trader, backend_token, backend_refresh_token
        )

        # Update session tokens if they were refreshed
        if new_access:
            logger.info(f"Backend token refreshed for trader {trader.id}")
            request.session["backend_access_token"] = new_access
            if new_refresh:
                request.session["backend_refresh_token"] = new_refresh

        # Return HTML response for htmx
        html_response = f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="bi bi-check-circle"></i> Product sync complete! {result['new']} new, {result['updated']} updated.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        <script>setTimeout(() => window.location.reload(), 1000);</script>
        """
        return HTMLResponse(content=html_response, status_code=200)

    except Exception as e:
        logger.error(f"Product sync failed for trader {trader.id}: {str(e)}")
        error_msg = str(e)
        if "expired" in error_msg.lower() or "401" in error_msg:
            error_msg = "Session expired. Please logout and login again."

        html_response = f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="bi bi-exclamation-circle"></i> Sync failed: {error_msg}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
        return HTMLResponse(content=html_response, status_code=500)


@router.post("/orders")
async def sync_orders(
    request: Request,
    trader: Trader = Depends(get_trader_from_session_or_bearer),
    db: AsyncSession = Depends(get_db),
):
    # Get backend tokens from session
    backend_token = request.session.get("backend_access_token", "")
    backend_refresh_token = request.session.get("backend_refresh_token", "")

    # Validate backend token exists
    if not backend_token:
        logger.warning(f"Sync orders failed - no backend token for trader {trader.id}")
        html_response = """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="bi bi-exclamation-circle"></i> Session expired. Please logout and login again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
        return HTMLResponse(content=html_response, status_code=401)

    logger.info(f"Sync orders initiated by trader {trader.id}")

    try:
        # Sync orders with auto token refresh
        result, new_access, new_refresh = await sync_orders_from_admin(
            db, trader, backend_token, backend_refresh_token
        )

        # Update session tokens if they were refreshed
        if new_access:
            logger.info(f"Backend token refreshed for trader {trader.id}")
            request.session["backend_access_token"] = new_access
            if new_refresh:
                request.session["backend_refresh_token"] = new_refresh

        # Return HTML response for htmx
        html_response = f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="bi bi-check-circle"></i> Order sync complete! {result['new']} new, {result['updated']} updated.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        <script>setTimeout(() => window.location.reload(), 1000);</script>
        """
        return HTMLResponse(content=html_response, status_code=200)

    except ValueError as e:
        # Specific error like "Trader not linked to backend user"
        logger.error(f"Order sync validation failed for trader {trader.id}: {str(e)}")
        html_response = f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="bi bi-exclamation-circle"></i> {str(e)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
        return HTMLResponse(content=html_response, status_code=400)

    except Exception as e:
        logger.error(f"Order sync failed for trader {trader.id}: {str(e)}")
        error_msg = str(e)
        if "expired" in error_msg.lower() or "401" in error_msg:
            error_msg = "Session expired. Please logout and login again."

        html_response = f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="bi bi-exclamation-circle"></i> Sync failed: {error_msg}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
        return HTMLResponse(content=html_response, status_code=500)
