from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime

from app.db.models import TraderProduct, Product, Category, AuditLog
from app.schemas.product import ProductUpdate, ProductResponse


FORBIDDEN_FIELDS = {"price", "central_stock", "category_id", "source_id", "version"}


async def get_trader_products(
    db: AsyncSession,
    trader_id: int,
    page: int = 1,
    limit: int = 10,
    category_id: int = None
) -> tuple[list[ProductResponse], int]:
    import logging
    logger = logging.getLogger(__name__)

    offset = (page - 1) * limit

    # Get category name if category_id is provided
    category_name = None
    if category_id:
        cat_result = await db.execute(select(Category.name).where(Category.id == category_id))
        category_name = cat_result.scalar_one_or_none()
        logger.info(f"Filtering by category_id={category_id}, name={category_name}")

    # Build base query
    query = (
        select(TraderProduct, Product, Category)
        .select_from(TraderProduct)
        .join(Product, TraderProduct.product_id == Product.id)
        .join(Category, Product.category_id == Category.id)
        .where(TraderProduct.trader_id == trader_id)
    )

    # Add category filter by name (to catch all duplicate category records)
    if category_name:
        query = query.where(Category.name == category_name)
        logger.info(f"Applied filter: Category.name == '{category_name}'")

    query = query.order_by(TraderProduct.display_order).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()
    logger.info(f"Found {len(rows)} products for trader={trader_id}, category_name={category_name}")
    products = []

    for trader_product, product, category in rows:
        logger.debug(f"  Product: {product.title}, Category: {category.name} (ID: {category.id})")
        products.append(ProductResponse(
            id=product.id,
            source_id=product.source_id,
            title=product.title,
            price=product.price,
            central_stock=product.central_stock,
            category_name=category.name,
            local_description=trader_product.local_description,
            local_notes=trader_product.local_notes,
            local_images=trader_product.local_images or [],
            visibility=trader_product.visibility,
            display_order=trader_product.display_order
        ))

    # Count query with category filter by name
    count_query = select(func.count(TraderProduct.id)).where(TraderProduct.trader_id == trader_id)
    if category_name:
        count_query = (
            count_query
            .select_from(TraderProduct)
            .join(Product, TraderProduct.product_id == Product.id)
            .join(Category, Product.category_id == Category.id)
            .where(and_(TraderProduct.trader_id == trader_id, Category.name == category_name))
        )

    count_result = await db.execute(count_query)
    total_count = count_result.scalar()

    return products, total_count


async def get_trader_categories(db: AsyncSession, trader_id: int) -> list[dict]:
    """Get all categories that have products for this trader"""
    # Get categories for this trader
    result = await db.execute(
        select(Category.id, Category.name)
        .select_from(Category)
        .join(Product, Product.category_id == Category.id)
        .join(TraderProduct, TraderProduct.product_id == Product.id)
        .where(TraderProduct.trader_id == trader_id)
        .order_by(Category.name)
    )

    # Deduplicate by name (keep first occurrence of each name)
    categories_dict = {}
    for cat_id, cat_name in result.all():
        if cat_name not in categories_dict:
            categories_dict[cat_name] = cat_id

    return [{"id": cat_id, "name": cat_name} for cat_name, cat_id in sorted(categories_dict.items())]


async def get_trader_product(db: AsyncSession, trader_id: int, product_id: int) -> ProductResponse:
    result = await db.execute(
        select(TraderProduct, Product, Category)
        .select_from(TraderProduct)
        .join(Product, TraderProduct.product_id == Product.id)
        .join(Category, Product.category_id == Category.id)
        .where(
            and_(
                TraderProduct.trader_id == trader_id,
                TraderProduct.product_id == product_id
            )
        )
    )

    row = result.first()
    if not row:
        raise ValueError("Product not found")

    trader_product, product, category = row
    return ProductResponse(
        id=product.id,
        source_id=product.source_id,
        title=product.title,
        price=product.price,
        central_stock=product.central_stock,
        category_name=category.name,
        local_description=trader_product.local_description,
        local_notes=trader_product.local_notes,
        local_images=trader_product.local_images or [],
        visibility=trader_product.visibility,
        display_order=trader_product.display_order
    )


async def update_trader_product(
    db: AsyncSession,
    trader_id: int,
    product_id: int,
    data: ProductUpdate
) -> ProductResponse:
    update_data = data.model_dump(exclude_unset=True)

    if any(field in update_data for field in FORBIDDEN_FIELDS):
        raise ValueError("Cannot modify admin-controlled fields")

    result = await db.execute(
        select(TraderProduct).where(
            and_(
                TraderProduct.trader_id == trader_id,
                TraderProduct.product_id == product_id
            )
        )
    )
    trader_product = result.scalar_one_or_none()

    if not trader_product:
        raise ValueError("Product not found or access denied")

    for field, value in update_data.items():
        if value is not None:
            setattr(trader_product, field, value)

    trader_product.updated_at = datetime.utcnow()
    await db.flush()

    audit_log = AuditLog(
        trader_id=trader_id,
        action="PRODUCT_UPDATE",
        entity="product",
        entity_id=product_id,
        audit_data=update_data
    )
    db.add(audit_log)
    await db.commit()

    product_result = await db.execute(
        select(TraderProduct, Product, Category)
        .select_from(TraderProduct)
        .join(Product, TraderProduct.product_id == Product.id)
        .join(Category, Product.category_id == Category.id)
        .where(TraderProduct.id == trader_product.id)
    )
    tp, product, category = product_result.first()

    return ProductResponse(
        id=product.id,
        source_id=product.source_id,
        title=product.title,
        price=product.price,
        central_stock=product.central_stock,
        category_name=category.name,
        local_description=tp.local_description,
        local_notes=tp.local_notes,
        local_images=tp.local_images or [],
        visibility=tp.visibility,
        display_order=tp.display_order
    )


async def update_product_order(
    db: AsyncSession,
    trader_id: int,
    product_orders: list[tuple[int, int]]
) -> dict:
    for product_id, display_order in product_orders:
        result = await db.execute(
            select(TraderProduct).where(
                and_(
                    TraderProduct.trader_id == trader_id,
                    TraderProduct.product_id == product_id
                )
            )
        )
        trader_product = result.scalar_one_or_none()
        if trader_product:
            trader_product.display_order = display_order
            trader_product.updated_at = datetime.utcnow()

    audit_log = AuditLog(
        trader_id=trader_id,
        action="PRODUCT_REORDER",
        entity="product",
        audit_data={"items": len(product_orders)}
    )
    db.add(audit_log)
    await db.commit()

    return {"message": "Product order updated"}
