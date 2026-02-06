from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from decimal import Decimal
from datetime import datetime
import logging

from app.db.session import get_db
from app.db.models import Order, OrderItem, Product, ShopCustomer, OrderStatus, TraderProduct
from app.schemas.order import OrderCreate, OrderResponse, OrderItemResponse, OrderListResponse
from app.api.dependencies import get_current_customer
from app.core.backend_client import backend_client
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    request: Request,
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new order from cart contents.
    1. Validate cart
    2. Send order to backend
    3. Save order locally
    4. Clear cart
    """
    # Get cart from session
    cart = request.session.get("cart", [])

    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Validate cart items and calculate total
    order_items = []
    total = Decimal("0.00")
    trader_id = settings.TRADER_ID

    for cart_item in cart:
        product_id = cart_item["product_id"]
        quantity = cart_item["quantity"]

        # Fetch product with validation
        result = await db.execute(
            select(Product, TraderProduct)
            .select_from(TraderProduct)
            .join(Product, TraderProduct.product_id == Product.id)
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
            raise HTTPException(
                status_code=400,
                detail=f"Product {product_id} not available"
            )

        product, _ = row

        # Check stock
        if product.central_stock < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.title}. Only {product.central_stock} available"
            )

        order_items.append({
            "product_id": product.id,
            "product_source_id": product.source_id,
            "product_title": product.title,
            "quantity": quantity,
            "price": product.price
        })
        total += product.price * quantity

    # Send order to backend (best effort - don't fail if backend unavailable)
    backend_order_id = None
    backend_status = "PENDING"

    try:
        backend_order = await backend_client.create_order(
            customer_email=order_data.customer_email,
            trader_id=trader_id,
            items=order_items,
            address=order_data.address,
            city=order_data.city,
            full_name=order_data.full_name,
            phone=order_data.phone
        )

        backend_order_id = backend_order.get("orderId")
        backend_status = backend_order.get("status", "PENDING")

        logger.info(f"Backend order created: {backend_order_id}")

    except Exception as e:
        logger.warning(f"Failed to create order on backend (will save locally): {str(e)}")
        # Generate a local-only source_id (negative to avoid conflicts with backend IDs)
        import time
        backend_order_id = -int(time.time() * 1000) % 2147483647  # Negative timestamp-based ID

    # Save order locally
    try:
        new_order = Order(
            source_id=backend_order_id,
            trader_id=trader_id,
            customer_email=order_data.customer_email,
            total=total,
            status=OrderStatus[backend_status] if backend_status in OrderStatus.__members__ else OrderStatus.PENDING,
            version="v1",
            synced_at=datetime.utcnow()
        )
        db.add(new_order)
        await db.flush()

        # Save order items
        for item in order_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                price_snapshot=item["price"]
            )
            db.add(order_item)

        await db.commit()
        await db.refresh(new_order)

        logger.info(f"Order saved locally: id={new_order.id}, source_id={backend_order_id}")

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save order locally: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Order created on backend but failed to save locally"
        )

    # Clear cart
    request.session["cart"] = []

    # Fetch order items for response
    items_result = await db.execute(
        select(OrderItem, Product)
        .select_from(OrderItem)
        .join(Product, OrderItem.product_id == Product.id)
        .where(OrderItem.order_id == new_order.id)
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

    return OrderResponse(
        id=new_order.id,
        source_id=new_order.source_id,
        customer_email=new_order.customer_email,
        total=new_order.total,
        status=new_order.status.value,
        created_at=new_order.created_at,
        items=items
    )


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    customer: ShopCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """List orders for authenticated customer."""
    trader_id = settings.TRADER_ID

    # Count total orders for this customer
    count_result = await db.execute(
        select(func.count(Order.id))
        .where(
            and_(
                Order.trader_id == trader_id,
                Order.customer_email == customer.email
            )
        )
    )
    total = count_result.scalar()

    # Fetch orders
    offset = (page - 1) * limit
    result = await db.execute(
        select(Order)
        .where(
            and_(
                Order.trader_id == trader_id,
                Order.customer_email == customer.email
            )
        )
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    orders = result.scalars().all()

    # Enrich with items
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

    return OrderListResponse(
        orders=order_responses,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    customer: ShopCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """Get single order detail."""
    trader_id = settings.TRADER_ID

    result = await db.execute(
        select(Order)
        .where(
            and_(
                Order.id == order_id,
                Order.trader_id == trader_id,
                Order.customer_email == customer.email
            )
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Fetch order items
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

    return OrderResponse(
        id=order.id,
        source_id=order.source_id,
        customer_email=order.customer_email,
        total=order.total,
        status=order.status.value,
        created_at=order.created_at,
        items=items
    )
