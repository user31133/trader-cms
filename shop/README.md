# Customer Web Shop

Customer-facing e-commerce shop for browsing products and placing orders.

## Features

- Customer registration and authentication (JWT)
- Browse products selected by trader
- Session-based shopping cart
- Order placement (integrated with backend)
- Order history for logged-in customers

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

3. Configure environment variables:
   - `DATABASE_URL`: PostgreSQL connection (shared with trader-cms)
   - `ADMIN_API_BASE_URL`: Main backend API URL
   - `TRADER_ID`: Which trader's products to show
   - `SHOP_NAME`: Display name for the shop
   - `JWT_SECRET_KEY`: Secret for customer JWT tokens
   - `SESSION_SECRET_KEY`: Secret for session management

4. Run database migrations (from trader-cms):
```bash
cd ../trader-cms
alembic upgrade head
```

5. Run the shop server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8001/api/docs
- ReDoc: http://localhost:8001/api/redoc

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new customer
- `POST /api/auth/login` - Customer login
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current customer info

### Products
- `GET /api/products` - List visible products (with pagination, filters)
- `GET /api/products/{id}` - Get product detail
- `GET /api/products/categories/all` - List categories

### Cart
- `GET /api/cart` - Get current cart
- `POST /api/cart/add` - Add item to cart
- `PUT /api/cart/update` - Update item quantity
- `DELETE /api/cart/remove/{product_id}` - Remove item
- `POST /api/cart/clear` - Clear cart

### Orders
- `POST /api/orders` - Create order (checkout)
- `GET /api/orders` - List customer orders (requires auth)
- `GET /api/orders/{id}` - Get order detail (requires auth)

## Architecture

### Single-Tenant Model
Each shop instance is configured for a specific trader via `TRADER_ID` in `.env`. The shop only shows products where:
- `TraderProduct.trader_id = {TRADER_ID}`
- `TraderProduct.visibility = True`

### Database
Shares the same PostgreSQL database with trader-cms. The shop reads from:
- `products` - Product master data
- `categories` - Product categories
- `trader_products` - Trader-specific product info
- `shop_customers` - Customer accounts (shop-specific)
- `orders` / `order_items` - Order data

### Order Flow
1. Customer adds products to cart (stored in session)
2. Customer proceeds to checkout
3. Shop validates cart items (stock, availability)
4. Shop sends order to main backend API
5. Backend creates order and returns order ID
6. Shop saves order locally in database
7. Shop clears cart
8. Customer sees order confirmation

### Security
- Customer authentication via JWT tokens
- Session-based cart (httponly cookies)
- Password hashing with bcrypt
- CORS configured for production
- All prices and stock validated before order creation

## Development

Run with auto-reload:
```bash
uvicorn app.main:app --reload --port 8001
```

Run tests:
```bash
pytest
```

## Deployment

### Environment Variables
Ensure all required environment variables are set in production:
- Use strong secrets for `JWT_SECRET_KEY` and `SESSION_SECRET_KEY`
- Set `ADMIN_API_BASE_URL` to production backend
- Configure `DATABASE_URL` with production credentials

### Running in Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

Or use Gunicorn:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

## Notes

- Frontend templates are NOT included in this backend implementation
- Use the API with any frontend framework (React, Vue, vanilla JS)
- Cart is session-based and expires after 7 days of inactivity
- Orders are sent to backend synchronously (consider async/queue for production)
- Stock validation happens at checkout time (not when adding to cart)
