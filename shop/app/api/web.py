from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from app.db.session import get_db
from app.api.products import list_products, get_product, list_categories
from app.api.cart import get_cart_with_details
from app.core.config import settings
from app.core.security import verify_password, hash_password
from app.db.models import ShopCustomer, Order, OrderItem, Product
from app.api.orders import create_order as api_create_order
from app.schemas.order import OrderCreate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")

# Helper to get common data for all templates
async def get_base_context(request: Request, db: AsyncSession):
    cart = await get_cart_with_details(request, db)
    cart_count = sum(item.quantity for item in cart.items)

    
    # Check if customer is logged in (from session)
    customer = None
    customer_id = request.session.get("customer_id")
    if customer_id:
        result = await db.execute(select(ShopCustomer).where(ShopCustomer.id == customer_id))
        customer_obj = result.scalar_one_or_none()
        # Convert to dict to avoid lazy loading issues after session closes
        if customer_obj:
            customer = {
                "id": customer_obj.id,
                "email": customer_obj.email,
                "full_name": customer_obj.full_name,
                "phone": customer_obj.phone,
                "address": customer_obj.address,
                "city": customer_obj.city
            }

    return {
        "request": request,
        "shop_name": settings.SHOP_NAME,
        "cart_count": cart_count,
        "customer": customer,
        "TRADER_ID": settings.TRADER_ID
    }

@router.get("/", response_class=HTMLResponse)
@router.get("/products", response_class=HTMLResponse)
async def home(
    request: Request,
    page: int = Query(1, ge=1),
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    base_context = await get_base_context(request, db)

    # Convert category_id from string to int, handle empty strings
    category_id_int = None
    if category_id and category_id.strip():
        try:
            category_id_int = int(category_id)
        except ValueError:
            category_id_int = None

    # Handle empty search strings
    search_term = search.strip() if search and search.strip() else None

    products_data = await list_products(page=page, limit=12, category_id=category_id_int, search=search_term, db=db)
    categories = await list_categories(db=db)
    
    return templates.TemplateResponse("home.html", {
        **base_context,
        "products": products_data.products,
        "total": products_data.total,
        "page": products_data.page,
        "total_pages": products_data.total_pages,
        "categories": categories,
        "current_category": category_id_int,
        "current_search": search_term
    })

@router.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    base_context = await get_base_context(request, db)
    product = await get_product(product_id=product_id, db=db)
    
    return templates.TemplateResponse("product_detail.html", {
        **base_context,
        "product": product
    })

@router.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request, db: AsyncSession = Depends(get_db)):
    base_context = await get_base_context(request, db)
    cart = await get_cart_with_details(request, db)

    return templates.TemplateResponse("cart.html", {
        **base_context,
        "cart": cart
    })

@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: AsyncSession = Depends(get_db)):
    base_context = await get_base_context(request, db)
    if not base_context["customer"]:
        return RedirectResponse(url="/login?next=/checkout", status_code=303)

    cart = await get_cart_with_details(request, db)
    if not cart.items:
        return templates.TemplateResponse("cart.html", {
            **base_context,
            "cart": cart,
            "error": "Your cart is empty"
        })
        
    return templates.TemplateResponse("checkout.html", {
        **base_context,
        "cart": cart
    })

@router.post("/checkout", response_class=HTMLResponse)
async def checkout_post(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    base_context = await get_base_context(request, db)
    if not base_context["customer"]:
        return RedirectResponse(url="/login?next=/checkout", status_code=303)
        
    order_data = OrderCreate(
        customer_email=email,
        full_name=full_name,
        phone=phone,
        address=address,
        city=city
    )
    
    from fastapi import HTTPException
    try:
        # Call the existing API logic
        order_response = await api_create_order(request, order_data, db)
        return RedirectResponse(url=f"/orders/{order_response.id}?success=true", status_code=303)
    except HTTPException as e:
        cart = await get_cart_with_details(request, db)
        return templates.TemplateResponse("checkout.html", {
            **base_context,
            "cart": cart,
            "error": e.detail,
            "form_data": order_data.dict()
        })
    except Exception as e:
        logger.error(f"Checkout error: {str(e)}")
        cart = await get_cart_with_details(request, db)
        return templates.TemplateResponse("checkout.html", {
            **base_context,
            "cart": cart,
            "error": "An unexpected error occurred during checkout",
            "form_data": order_data.dict()
        })

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/", db: AsyncSession = Depends(get_db)):
    base_context = await get_base_context(request, db)
    return templates.TemplateResponse("auth/login.html", {
        **base_context,
        "next": next
    })

@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = "/",
    db: AsyncSession = Depends(get_db)
):
    base_context = await get_base_context(request, db)
    
    result = await db.execute(select(ShopCustomer).where(ShopCustomer.email == email))
    customer = result.scalar_one_or_none()
    
    if not customer or not verify_password(password, customer.password_hash):
        return templates.TemplateResponse("auth/login.html", {
            **base_context,
            "error": "Invalid email or password",
            "email": email,
            "next": next
        })
        
    request.session["customer_id"] = customer.id
    return RedirectResponse(url=next, status_code=303)

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: AsyncSession = Depends(get_db)):
    base_context = await get_base_context(request, db)
    return templates.TemplateResponse("auth/register.html", {**base_context})

@router.post("/register", response_class=HTMLResponse)
async def register_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    base_context = await get_base_context(request, db)
    
    # Check if exists
    result = await db.execute(select(ShopCustomer).where(ShopCustomer.email == email))
    if result.scalar_one_or_none():
        return templates.TemplateResponse("auth/register.html", {
            **base_context,
            "error": "Email already registered",
            "form_data": {
                "email": email,
                "full_name": full_name,
                "phone": phone,
                "address": address,
                "city": city
            }
        })
        
    new_customer = ShopCustomer(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        phone=phone,
        address=address,
        city=city
    )
    db.add(new_customer)
    await db.commit()
    await db.refresh(new_customer)
    
    request.session["customer_id"] = new_customer.id
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@router.get("/orders", response_class=HTMLResponse)
async def order_history(request: Request, db: AsyncSession = Depends(get_db)):
    base_context = await get_base_context(request, db)
    if not base_context["customer"]:
        return RedirectResponse(url="/login?next=/orders", status_code=303)

    customer = base_context["customer"]
    result = await db.execute(
        select(Order)
        .where(Order.customer_email == customer["email"])
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    
    return templates.TemplateResponse("orders.html", {
        **base_context,
        "orders": orders
    })

@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail_page(request: Request, order_id: int, success: bool = False, db: AsyncSession = Depends(get_db)):
    base_context = await get_base_context(request, db)
    if not base_context["customer"]:
        return RedirectResponse(url=f"/login?next=/orders/{order_id}", status_code=303)
        
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id, Order.customer_email == base_context["customer"]["email"])
    )
    order = result.scalar_one_or_none()
    
    if not order:
        return HTMLResponse(content="Order not found", status_code=404)
        
    return templates.TemplateResponse("order_detail.html", {
        **base_context,
        "order": order,
        "success": success
    })
