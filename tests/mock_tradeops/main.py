"""Mock tradeops backend for e2e tests. Returns hardcoded hierarchical categories."""
from fastapi import FastAPI, Request

app = FastAPI(title="Mock Tradeops")

CATEGORIES = [
    {
        "id": 1,
        "name": "Electronics",
        "slug": "electronics",
        "parentId": None,
        "isActive": True,
        "sortOrder": 0,
        "subcategories": [
            {
                "id": 3,
                "name": "Phones",
                "slug": "phones",
                "parentId": 1,
                "isActive": True,
                "sortOrder": 0,
                "subcategories": [],
            },
            {
                "id": 4,
                "name": "Laptops",
                "slug": "laptops",
                "parentId": 1,
                "isActive": True,
                "sortOrder": 1,
                "subcategories": [],
            },
        ],
    },
    {
        "id": 2,
        "name": "Clothing",
        "slug": "clothing",
        "parentId": None,
        "isActive": True,
        "sortOrder": 1,
        "subcategories": [
            {
                "id": 5,
                "name": "T-Shirts",
                "slug": "t-shirts",
                "parentId": 2,
                "isActive": True,
                "sortOrder": 0,
                "subcategories": [],
            },
        ],
    },
]

PRODUCTS = [
    {"id": 1, "name": "iPhone 15", "categoryId": 3, "basePrice": 999.99, "availableQty": 50},
    {"id": 2, "name": "MacBook Pro", "categoryId": 4, "basePrice": 1999.99, "availableQty": 20},
    {"id": 3, "name": "Basic Tee", "categoryId": 5, "basePrice": 29.99, "availableQty": 100},
]


@app.post("/api/v1/auth/register-trader")
async def register_trader(request: Request):
    return {"user": {"id": 1, "email": "test@test.com", "fullName": "Test Shop"}}


@app.post("/api/v1/auth/login")
async def login(request: Request):
    return {
        "accessToken": "mock-access-token",
        "refreshToken": "mock-refresh-token",
        "isOtpRequired": False,
    }


@app.post("/api/v1/auth/refresh")
async def refresh(request: Request):
    return {
        "accessToken": "mock-access-token-refreshed",
        "refreshToken": "mock-refresh-token",
    }


@app.get("/api/v1/admin/catalog/categories")
async def admin_categories():
    return {
        "content": CATEGORIES,
        "totalElements": len(CATEGORIES),
        "totalPages": 1,
        "number": 0,
        "size": 20,
    }


@app.get("/api/v1/catalog/products")
async def catalog_products(
    traderId: int = 1,
    categoryId: int = None,
    query: str = None,
    page: int = 0,
    size: int = 20,
):
    products = PRODUCTS
    if categoryId:
        products = [p for p in products if p["categoryId"] == categoryId]
    if query:
        products = [p for p in products if query.lower() in p["name"].lower()]
    return {
        "content": products,
        "totalElements": len(products),
        "totalPages": 1,
        "number": page,
        "size": size,
    }


@app.put("/api/v1/trader/{trader_id}/config/categories")
async def update_allowed_categories(trader_id: int, request: Request):
    return {"message": "Updated"}


@app.get("/api/v1/trader/orders")
async def trader_orders():
    return {"content": [], "totalElements": 0, "totalPages": 0, "number": 0}


@app.get("/health")
async def health():
    return {"status": "ok"}
