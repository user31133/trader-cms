from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
from typing import List, Dict, Any
from app.db.models import Product, Category, TraderProduct, AuditLog, CartItem


class SelectionCartService:
    """Manages product selection cart in database"""

    @staticmethod
    async def get_cart(db: AsyncSession, trader_id: int) -> List[int]:
        """Get cart items for trader"""
        result = await db.execute(
            select(CartItem.product_source_id)
            .where(CartItem.trader_id == trader_id)
            .order_by(CartItem.created_at)
        )
        return [row[0] for row in result.all()]

    @staticmethod
    async def add_to_cart(db: AsyncSession, trader_id: int, product_source_ids: List[int]) -> List[int]:
        """Add products to cart"""
        for source_id in product_source_ids:
            # Check if already in cart
            existing = await db.execute(
                select(CartItem).where(
                    CartItem.trader_id == trader_id,
                    CartItem.product_source_id == source_id
                )
            )
            if not existing.scalar_one_or_none():
                cart_item = CartItem(
                    trader_id=trader_id,
                    product_source_id=source_id
                )
                db.add(cart_item)

        await db.commit()
        return await SelectionCartService.get_cart(db, trader_id)

    @staticmethod
    async def remove_from_cart(db: AsyncSession, trader_id: int, product_source_ids: List[int]) -> List[int]:
        """Remove products from cart"""
        await db.execute(
            delete(CartItem).where(
                CartItem.trader_id == trader_id,
                CartItem.product_source_id.in_(product_source_ids)
            )
        )
        await db.commit()
        return await SelectionCartService.get_cart(db, trader_id)

    @staticmethod
    async def clear_cart(db: AsyncSession, trader_id: int):
        """Clear all cart items for trader"""
        await db.execute(
            delete(CartItem).where(CartItem.trader_id == trader_id)
        )
        await db.commit()


async def save_selected_products(
    db: AsyncSession,
    trader_id: int,
    selected_source_ids: List[int],
    available_products: List[Dict[str, Any]]
) -> dict:
    """
    Save selected products to trader's product list.
    Creates Product, Category, and TraderProduct records.
    Similar to sync_products_from_admin but only for selected items.
    """
    created_count = 0
    updated_count = 0

    for product_data in available_products:
        if product_data["sourceId"] not in selected_source_ids:
            continue

        # Create/update category - use NAME instead of source_id because backend source_ids are unreliable
        import logging
        logger = logging.getLogger(__name__)

        # First try to find category by name
        category_result = await db.execute(
            select(Category).where(Category.name == product_data["category"]["name"])
        )
        category = category_result.first()

        if category:
            category = category[0]  # Extract from tuple
            logger.info(f"Using existing category by name: id={category.id}, name={category.name}, source_id={category.source_id}")
        else:
            # Create new category with the name and source_id from backend
            logger.info(f"Creating new category: source_id={product_data['category']['sourceId']}, name={product_data['category']['name']}")
            category = Category(
                source_id=product_data["category"]["sourceId"],
                name=product_data["category"]["name"],
                version="v1",
                synced_at=datetime.utcnow()
            )
            db.add(category)
            await db.flush()

        # Create/update product
        product_result = await db.execute(
            select(Product).where(Product.source_id == product_data["sourceId"])
        )
        product = product_result.scalar_one_or_none()

        if product:
            logger.info(f"Updating product: {product_data['title']}, category_id={category.id}")
            product.title = product_data["title"]
            product.price = product_data["price"]
            product.central_stock = product_data["centralStock"]
            product.category_id = category.id
            product.version = product_data["version"]
            product.synced_at = datetime.utcnow()
            updated_count += 1
        else:
            logger.info(f"Creating product: {product_data['title']}, category_id={category.id}, category_name={category.name}")
            product = Product(
                source_id=product_data["sourceId"],
                title=product_data["title"],
                price=product_data["price"],
                central_stock=product_data["centralStock"],
                category_id=category.id,
                version=product_data["version"],
                synced_at=datetime.utcnow()
            )
            db.add(product)
            await db.flush()
            created_count += 1

        # Create TraderProduct link if doesn't exist
        tp_result = await db.execute(
            select(TraderProduct).where(
                TraderProduct.trader_id == trader_id,
                TraderProduct.product_id == product.id
            )
        )
        trader_product = tp_result.scalar_one_or_none()

        if not trader_product:
            trader_product = TraderProduct(
                trader_id=trader_id,
                product_id=product.id,
                visibility=True,
                display_order=0
            )
            db.add(trader_product)

    # Audit log
    audit_log = AuditLog(
        trader_id=trader_id,
        action="SAVE_SELECTION",
        entity="product",
        audit_data={
            "selected": len(selected_source_ids),
            "created": created_count,
            "updated": updated_count
        }
    )
    db.add(audit_log)
    await db.commit()

    return {
        "saved": created_count + updated_count,
        "created": created_count,
        "updated": updated_count
    }
