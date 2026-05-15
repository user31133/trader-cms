from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.db.session import get_db
from app.db.models import ShopCustomer
from app.schemas.customer import (
    CustomerRegister,
    CustomerLogin,
    CustomerResponse,
    TokenResponse,
    RefreshTokenRequest
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.api.dependencies import get_current_customer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    customer_data: CustomerRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register a new customer."""
    # Check if email already exists
    result = await db.execute(
        select(ShopCustomer).where(ShopCustomer.email == customer_data.email)
    )
    existing_customer = result.scalar_one_or_none()

    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new customer
    new_customer = ShopCustomer(
        email=customer_data.email,
        password_hash=hash_password(customer_data.password),
        full_name=customer_data.full_name,
        phone=customer_data.phone,
        address=customer_data.address,
        city=customer_data.city
    )

    db.add(new_customer)
    await db.commit()
    await db.refresh(new_customer)

    logger.info(f"New customer registered: {new_customer.email}")

    # Generate tokens
    access_token = create_access_token({"sub": str(new_customer.id)})
    refresh_token = create_refresh_token({"sub": str(new_customer.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        customer=CustomerResponse.from_orm(new_customer)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: CustomerLogin,
    db: AsyncSession = Depends(get_db)
):
    """Customer login."""
    # Find customer by email
    result = await db.execute(
        select(ShopCustomer).where(ShopCustomer.email == credentials.email)
    )
    customer = result.scalar_one_or_none()

    if not customer or not verify_password(credentials.password, customer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    logger.info(f"Customer logged in: {customer.email}")

    # Generate tokens
    access_token = create_access_token({"sub": str(customer.id)})
    refresh_token = create_refresh_token({"sub": str(customer.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        customer=CustomerResponse.from_orm(customer)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    payload = verify_token(token_data.refresh_token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    customer_id = int(payload["sub"])
    result = await db.execute(
        select(ShopCustomer).where(ShopCustomer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer not found"
        )

    # Generate new tokens
    access_token = create_access_token({"sub": str(customer.id)})
    refresh_token = create_refresh_token({"sub": str(customer.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        customer=CustomerResponse.from_orm(customer)
    )


@router.get("/me", response_model=CustomerResponse)
async def get_current_customer_info(
    customer: ShopCustomer = Depends(get_current_customer)
):
    """Get current customer information."""
    return CustomerResponse.from_orm(customer)
