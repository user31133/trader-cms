import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.api import auth, products, cart, orders, web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=f"{settings.SHOP_NAME} - Customer Shop",
    description="Customer-facing e-commerce shop API",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Add session middleware for cart management
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    max_age=3600 * 24 * 7  # 7 days
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(web.router)




@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "shop_name": settings.SHOP_NAME,
        "trader_id": settings.TRADER_ID
    }


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.SHOP_NAME} shop for trader {settings.TRADER_ID}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down shop application")
    # Close backend client
    from app.core.backend_client import backend_client
    await backend_client.close()
