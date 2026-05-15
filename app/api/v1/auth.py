import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest
from app.services.auth import register_trader, login, refresh_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"Received registration request for email: {request.email}")
    try:
        trader = await register_trader(db, request)
        logger.info(f"Registration completed for email: {request.email}, trader id: {trader.id}")
        return {
            "id": trader.id,
            "email": trader.email,
            "business_name": trader.business_name,
            "status": trader.status
        }
    except ValueError as e:
        logger.warning(f"Registration validation error for {request.email}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login_route(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        token = await login(db, request.email, request.password)
        return token
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_route(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        token = await refresh_access_token(db, request.refresh_token)
        return token
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    return {"message": "Logged out successfully"}
