from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from decimal import Decimal
import logging

from app.db.session import get_db
from app.db.models import Product, TraderProduct
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartItemResponse, CartResponse
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cart", tags=["cart"])


def get_cart_from_session(request: Request) -> list:
    """Get cart items from session."""
    return request.session.get("cart", [])


def save_cart_to_session(request: Request, cart: list):
    """Save cart items to session."""
    request.session["cart"] = cart


async def get_cart_with_details(request: Request, db: AsyncSession) -> CartResponse:
    """Helper function to get cart with product details. Used by web routes."""
    cart = get_cart_from_session(request)

    if not cart:
        return CartResponse(items=[], total=Decimal("0.00"), item_count=0)

    # Enrich cart items with product details
    items = []
    total = Decimal("0.00")

    for cart_item in cart:
        product_id = cart_item["product_id"]
        quantity = cart_item["quantity"]

        # Fetch product details
        result = await db.execute(
            select(Product)
            .where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if product:
            subtotal = product.price * quantity
            items.append(CartItemResponse(
                product_id=product.id,
                product_title=product.title,
                product_price=product.price,
                quantity=quantity,
                subtotal=subtotal
            ))
            total += subtotal

    return CartResponse(
        items=items,
        total=total,
        item_count=len(items)
    )


async def validate_product(db: AsyncSession, product_id: int, quantity: int) -> tuple[Product, TraderProduct]:
    """
    Validate that product exists, is visible, and has enough stock.
    Returns (Product, TraderProduct) if valid, raises HTTPException otherwise.
    """
    trader_id = settings.TRADER_ID

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
        raise HTTPException(status_code=404, detail="Product not found or not available")

    product, trader_product = row

    if product.central_stock < quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Only {product.central_stock} units available"
        )

    return product, trader_product


@router.get("", response_model=CartResponse)
async def get_cart(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current shopping cart."""
    cart = get_cart_from_session(request)

    if not cart:
        return CartResponse(items=[], total=Decimal("0.00"), item_count=0)

    # Enrich cart items with product details
    items = []
    total = Decimal("0.00")

    for cart_item in cart:
        product_id = cart_item["product_id"]
        quantity = cart_item["quantity"]

        # Fetch product details
        result = await db.execute(
            select(Product)
            .where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if product:
            subtotal = product.price * quantity
            items.append(CartItemResponse(
                product_id=product.id,
                product_title=product.title,
                product_price=product.price,
                quantity=quantity,
                subtotal=subtotal
            ))
            total += subtotal

    return CartResponse(
        items=items,
        total=total,
        item_count=len(items)
    )


@router.post("/add", response_model=CartResponse)
async def add_to_cart(
    request: Request,
    item: CartItemAdd,
    db: AsyncSession = Depends(get_db)
):
    """Add item to cart."""
    # Validate product
    await validate_product(db, item.product_id, item.quantity)

    cart = get_cart_from_session(request)

    # Check if item already in cart
    existing_item = next((ci for ci in cart if ci["product_id"] == item.product_id), None)

    if existing_item:
        # Update quantity
        new_quantity = existing_item["quantity"] + item.quantity
        # Validate new quantity
        await validate_product(db, item.product_id, new_quantity)
        existing_item["quantity"] = new_quantity
    else:
        # Add new item
        cart.append({
            "product_id": item.product_id,
            "quantity": item.quantity
        })

    save_cart_to_session(request, cart)
    logger.info(f"Added to cart: product_id={item.product_id}, quantity={item.quantity}")

    return await get_cart(request, db)


@router.put("/update", response_model=CartResponse)
async def update_cart_item(
    request: Request,
    item: CartItemUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update cart item quantity."""
    if item.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    # Validate product and quantity
    await validate_product(db, item.product_id, item.quantity)

    cart = get_cart_from_session(request)

    # Find and update item
    cart_item = next((ci for ci in cart if ci["product_id"] == item.product_id), None)

    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not in cart")

    cart_item["quantity"] = item.quantity
    save_cart_to_session(request, cart)
    logger.info(f"Updated cart item: product_id={item.product_id}, quantity={item.quantity}")

    return await get_cart(request, db)


@router.delete("/remove/{product_id}", response_model=CartResponse)
async def remove_from_cart(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove item from cart."""
    cart = get_cart_from_session(request)

    # Filter out the item
    cart = [ci for ci in cart if ci["product_id"] != product_id]

    save_cart_to_session(request, cart)
    logger.info(f"Removed from cart: product_id={product_id}")

    return await get_cart(request, db)


@router.post("/clear", response_model=CartResponse)
async def clear_cart(request: Request, db: AsyncSession = Depends(get_db)):
    """Clear entire cart."""
    save_cart_to_session(request, [])
    logger.info("Cart cleared")
    return CartResponse(items=[], total=Decimal("0.00"), item_count=0)
