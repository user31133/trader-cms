from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal

from app.db.models import Order, OrderItem, Product, OrderStatus
from app.schemas.order import OrderResponse, OrderItemResponse, OrderStats


async def get_trader_orders(
    db: AsyncSession,
    trader_id: int,
    page: int = 1,
    limit: int = 10
) -> tuple[list[OrderResponse], int]:
    offset = (page - 1) * limit

    result = await db.execute(
        select(Order).where(Order.trader_id == trader_id).order_by(Order.created_at.desc()).offset(offset).limit(limit)
    )
    orders = result.scalars().all()

    count_result = await db.execute(
        select(func.count(Order.id)).where(Order.trader_id == trader_id)
    )
    total_count = count_result.scalar()

    order_responses = []
    for order in orders:
        items_result = await db.execute(
            select(OrderItem, Product)
            .select_from(OrderItem)
            .join(Product, OrderItem.product_id == Product.id)
            .where(OrderItem.order_id == order.id)
        )
        items_rows = items_result.all()

        items = [
            OrderItemResponse(
                product_id=item.product_id,
                product_title=product.title,
                quantity=item.quantity,
                price_snapshot=item.price_snapshot
            )
            for item, product in items_rows
        ]

        order_responses.append(OrderResponse(
            id=order.id,
            source_id=order.source_id,
            customer_email=order.customer_email,
            total=order.total,
            status=order.status.value,
            created_at=order.created_at,
            items=items
        ))

    return order_responses, total_count


async def get_trader_stats(db: AsyncSession, trader_id: int) -> OrderStats:
    total_result = await db.execute(
        select(func.count(Order.id), func.sum(Order.total)).where(Order.trader_id == trader_id)
    )
    total_count, total_revenue = total_result.first()

    pending_result = await db.execute(
        select(func.count(Order.id)).where(
            (Order.trader_id == trader_id) & (Order.status == OrderStatus.PENDING)
        )
    )
    pending_count = pending_result.scalar()

    return OrderStats(
        total_orders=total_count or 0,
        total_revenue=total_revenue or Decimal("0.00"),
        pending_orders=pending_count or 0
    )
