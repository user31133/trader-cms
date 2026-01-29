from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
import logging

from app.db.session import get_db
from app.db.models import Product, Category, TraderProduct
from app.schemas.product import ProductResponse, ProductListResponse, CategoryResponse
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List visible products for this shop's trader.
    Only shows products where TraderProduct.visibility = True.
    """
    trader_id = settings.TRADER_ID

    # Build base query
    query = (
        select(Product, TraderProduct, Category)
        .select_from(TraderProduct)
        .join(Product, TraderProduct.product_id == Product.id)
        .join(Category, Product.category_id == Category.id)
        .where(
            and_(
                TraderProduct.trader_id == trader_id,
                TraderProduct.visibility == True
            )
        )
    )

    # Apply category filter
    if category_id:
        query = query.where(Product.category_id == category_id)

    # Apply search filter
    if search:
        query = query.where(Product.title.ilike(f"%{search}%"))

    # Order by display_order, then by title
    query = query.order_by(TraderProduct.display_order.desc(), Product.title)

    # Count total
    count_query = (
        select(func.count())
        .select_from(TraderProduct)
        .join(Product, TraderProduct.product_id == Product.id)
        .where(
            and_(
                TraderProduct.trader_id == trader_id,
                TraderProduct.visibility == True
            )
        )
    )
    if category_id:
        count_query = count_query.where(Product.category_id == category_id)
    if search:
        count_query = count_query.where(Product.title.ilike(f"%{search}%"))

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Paginate
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    # Transform to response format
    products = []
    for product, trader_product, category in rows:
        products.append(ProductResponse(
            id=product.id,
            source_id=product.source_id,
            title=product.title,
            price=product.price,
            stock=product.central_stock,
            category=CategoryResponse(id=category.id, name=category.name),
            local_description=trader_product.local_description,
            local_notes=trader_product.local_notes,
            local_images=trader_product.local_images or [],
            display_order=trader_product.display_order
        ))

    total_pages = (total + limit - 1) // limit

    return ProductListResponse(
        products=products,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get single product detail."""
    trader_id = settings.TRADER_ID

    result = await db.execute(
        select(Product, TraderProduct, Category)
        .select_from(TraderProduct)
        .join(Product, TraderProduct.product_id == Product.id)
        .join(Category, Product.category_id == Category.id)
        .where(
            and_(
                TraderProduct.trader_id == trader_id,
                TraderProduct.visibility == True,
                Product.id == product_id
            )
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    product, trader_product, category = row

    return ProductResponse(
        id=product.id,
        source_id=product.source_id,
        title=product.title,
        price=product.price,
        stock=product.central_stock,
        category=CategoryResponse(id=category.id, name=category.name),
        local_description=trader_product.local_description,
        local_notes=trader_product.local_notes,
        local_images=trader_product.local_images or [],
        display_order=trader_product.display_order
    )


@router.get("/categories/all", response_model=List[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all categories that have visible products for this trader."""
    trader_id = settings.TRADER_ID

    result = await db.execute(
        select(Category)
        .distinct()
        .select_from(TraderProduct)
        .join(Product, TraderProduct.product_id == Product.id)
        .join(Category, Product.category_id == Category.id)
        .where(
            and_(
                TraderProduct.trader_id == trader_id,
                TraderProduct.visibility == True
            )
        )
        .order_by(Category.name)
    )
    categories = result.scalars().all()

    return [CategoryResponse(id=cat.id, name=cat.name) for cat in categories]
