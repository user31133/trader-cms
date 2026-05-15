from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import ShopCustomer
from app.core.security import verify_token

security = HTTPBearer()


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> ShopCustomer:
    """
    Dependency to get current authenticated customer from JWT token.
    """
    token = credentials.credentials
    payload = verify_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
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

    return customer


async def get_optional_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> ShopCustomer | None:
    """
    Optional authentication - returns customer if valid token, None otherwise.
    """
    try:
        return await get_current_customer(credentials, db)
    except HTTPException:
        return None
