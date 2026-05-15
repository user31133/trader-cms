from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import uuid
from pathlib import Path

from app.api.dependencies import get_current_trader
from app.db.session import get_db
from app.db.models import Trader, TraderStatus
from app.core.security import verify_token
from app.schemas.product import ProductUpdate, ProductResponse
from app.services.product import get_trader_products, get_trader_product, update_trader_product, update_product_order
from app.core.config import settings


router = APIRouter(prefix="/api/v1/trader", tags=["products"])


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


@router.get("/products", response_model=dict)
async def list_products(
    page: int = 1,
    limit: int = 10,
    trader: Trader = Depends(get_trader_from_session_or_bearer),
    db: AsyncSession = Depends(get_db)
):
    try:
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10

        products, total_count = await get_trader_products(db, trader.id, page, limit)
        total_pages = (total_count + limit - 1) // limit

        return {
            "items": products,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    trader: Trader = Depends(get_trader_from_session_or_bearer),
    db: AsyncSession = Depends(get_db)
):
    try:
        product = await get_trader_product(db, trader.id, product_id)
        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    trader: Trader = Depends(get_trader_from_session_or_bearer),
    db: AsyncSession = Depends(get_db)
):
    try:
        updated = await update_trader_product(db, trader.id, product_id, data)
        return updated
    except ValueError as e:
        if "Cannot modify" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/products/reorder")
async def reorder_products(
    orders: list[dict],
    trader: Trader = Depends(get_trader_from_session_or_bearer),
    db: AsyncSession = Depends(get_db)
):
    try:
        product_orders = [(item["product_id"], item["display_order"]) for item in orders]
        result = await update_product_order(db, trader.id, product_orders)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/products/{product_id}/upload-image")
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    trader: Trader = Depends(get_trader_from_session_or_bearer),
    db: AsyncSession = Depends(get_db)
):
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
        )

    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)

    if file_size_mb > settings.MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_IMAGE_SIZE_MB}MB"
        )

    try:
        await get_trader_product(db, trader.id, product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    upload_dir = Path(settings.UPLOAD_DIR) / str(trader.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    with open(file_path, "wb") as f:
        f.write(file_content)

    image_url = f"/static/uploads/{trader.id}/{unique_filename}"

    return {
        "url": image_url,
        "filename": unique_filename,
        "size": len(file_content)
    }
