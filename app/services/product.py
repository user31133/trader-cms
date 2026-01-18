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
    limit: int = 10
) -> tuple[list[ProductResponse], int]:
    offset = (page - 1) * limit

    result = await db.execute(
        select(TraderProduct, Product, Category)
        .select_from(TraderProduct)
        .join(Product, TraderProduct.product_id == Product.id)
        .join(Category, Product.category_id == Category.id)
        .where(TraderProduct.trader_id == trader_id)
        .order_by(TraderProduct.display_order)
        .offset(offset)
        .limit(limit)
    )

    rows = result.all()
    products = []

    for trader_product, product, category in rows:
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

    count_result = await db.execute(
        select(func.count(TraderProduct.id)).where(TraderProduct.trader_id == trader_id)
    )
    total_count = count_result.scalar()

    return products, total_count


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
