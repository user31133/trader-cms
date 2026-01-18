from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.db.models import Trader, Category, Product, TraderProduct, Order, OrderItem, AuditLog, OrderStatus
from app.core.admin_client import admin_client


async def sync_products_from_admin(db: AsyncSession, trader: Trader, access_token: str) -> dict:
    response = await admin_client.sync_products(access_token=access_token, api_key=trader.api_key or "")

    new_count = 0
    updated_count = 0

    for item in response["products"]:
        category_result = await db.execute(select(Category).where(Category.source_id == item["sourceId"]))
        category = category_result.scalar_one_or_none()

        if not category:
            category = Category(
                source_id=item["sourceId"],
                name=item["category"],
                version="v1",
                synced_at=datetime.utcnow()
            )
            db.add(category)
            await db.flush()

        product_result = await db.execute(select(Product).where(Product.source_id == item["sourceId"]))
        product = product_result.scalar_one_or_none()

        if product:
            if product.version != item["version"]:
                product.price = item["price"]
                product.central_stock = item["centralStock"]
                product.version = item["version"]
                product.synced_at = datetime.utcnow()
                updated_count += 1
        else:
            product = Product(
                source_id=item["sourceId"],
                title=item["title"],
                price=item["price"],
                central_stock=item["centralStock"],
                category_id=category.id,
                version=item["version"],
                synced_at=datetime.utcnow()
            )
            db.add(product)
            await db.flush()
            new_count += 1

        tp_result = await db.execute(
            select(TraderProduct).where(
                TraderProduct.trader_id == trader.id,
                TraderProduct.product_id == product.id
            )
        )
        trader_product = tp_result.scalar_one_or_none()

        if not trader_product:
            trader_product = TraderProduct(
                trader_id=trader.id,
                product_id=product.id,
                local_images=[],
                visibility=True
            )
            db.add(trader_product)

    audit_log = AuditLog(
        trader_id=trader.id,
        action="SYNC",
        entity="product",
        audit_data={"new": new_count, "updated": updated_count}
    )
    db.add(audit_log)
    await db.commit()

    return {
        "synced": new_count + updated_count,
        "new": new_count,
        "updated": updated_count
    }


async def sync_orders_from_admin(db: AsyncSession, trader: Trader, access_token: str) -> dict:
    if not trader.backend_user_id:
        raise ValueError("Trader not linked to backend user. Please re-register.")

    response = await admin_client.sync_orders(
        backend_user_id=trader.backend_user_id,
        access_token=access_token,
        api_key=trader.api_key or ""
    )

    new_count = 0
    updated_count = 0

    for item in response["orders"]:
        order_result = await db.execute(select(Order).where(Order.source_id == item["sourceId"]))
        order = order_result.scalar_one_or_none()

        # Parse the createdAt timestamp
        created_at = datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00"))

        if order:
            # Update existing order if version changed
            if order.version != item.get("version", ""):
                order.total = item["totalPrice"]
                order.status = OrderStatus[item["status"]]
                order.version = item.get("version", "")
                order.synced_at = datetime.utcnow()
                updated_count += 1
        else:
            # Create new order
            order = Order(
                source_id=item["sourceId"],
                trader_id=trader.id,
                total=item["totalPrice"],
                status=OrderStatus[item["status"]],
                created_at=created_at,
                synced_at=datetime.utcnow(),
                version=item.get("version", "")
            )
            db.add(order)
            await db.flush()

            # Add order items
            for order_item in item["items"]:
                product_result = await db.execute(
                    select(Product).where(Product.source_id == order_item["productId"])
                )
                product = product_result.scalar_one_or_none()

                if product:
                    order_item_obj = OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=order_item["quantity"],
                        price_snapshot=order_item["priceAtPurchase"]
                    )
                    db.add(order_item_obj)

            new_count += 1

    audit_log = AuditLog(
        trader_id=trader.id,
        action="SYNC_ORDERS",
        entity="order",
        audit_data={"new": new_count, "updated": updated_count}
    )
    db.add(audit_log)
    await db.commit()

    return {
        "synced": new_count + updated_count,
        "new": new_count,
        "updated": updated_count
    }
