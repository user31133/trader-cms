# Broker CMS - Complete E-Commerce System

Complete e-commerce platform with **Trader CMS** (admin panel) and **Customer Shop** (storefront).

## 🚀 Quick Start with Docker (Recommended)

### Prerequisites
- Docker Desktop installed and running

### Start All Services

```bash
docker compose up --build
```

This starts:
- **PostgreSQL Database** (port 5432)
- **Trader CMS** (port 8000) - Admin panel
- **Customer Shop** (port 8001) - Storefront

### Access Applications

**Trader CMS (Admin Panel)**
- http://localhost:8000
- API Docs: http://localhost:8000/api/docs

**Customer Shop (Storefront)**
- http://localhost:8001
- API Docs: http://localhost:8001/api/docs

### Stop Services

```bash
docker compose down
```

## 📦 Manual Installation (Without Docker)

### Prerequisites
- Python 3.11+
- PostgreSQL 15+

### 1. Trader CMS

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8000 --reload
```

### 2. Customer Shop

```bash
cd shop
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload
```

## API Documentation

- OpenAPI/Swagger: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Architecture

### Core Components

**Authentication**
- JWT-based (access + refresh tokens)
- POST `/api/v1/auth/register` - Register trader
- POST `/api/v1/auth/login` - Login
- POST `/api/v1/auth/refresh` - Refresh token

**Product Sync**
- POST `/api/v1/sync/products` - Sync from Admin API
- GET `/api/v1/trader/products` - List products
- PATCH `/api/v1/trader/products/{id}` - Edit local fields
- POST `/api/v1/trader/products/reorder` - Reorder products

**Customer Management**
- POST `/api/v1/trader/customers` - Create customer
- GET `/api/v1/trader/customers` - List customers
- GET `/api/v1/trader/customers/{id}` - Get customer

**Orders**
- GET `/api/v1/trader/orders` - List orders (read-only)
- GET `/api/v1/trader/stats` - Order statistics

## Database Schema

**Core Tables**
- `traders` - Trader accounts (PENDING/ACTIVE/REJECTED)
- `products` - Synced from Admin (price, stock read-only)
- `trader_products` - Local customizations (description, images, visibility)
- `customers` - Customer accounts created by traders
- `orders` - Orders synced from Admin (read-only)
- `order_items` - Order line items
- `categories` - Product categories (synced from Admin)
- `audit_logs` - All actions for compliance

## Configuration

### Environment Variables (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/trader_cms

# Admin API
ADMIN_API_BASE_URL=http://localhost:8080/api/v1

# JWT
JWT_SECRET_KEY=your-secret-key-generate-new-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Session
SESSION_SECRET_KEY=another-secret-key-for-sessions

# File Upload
MAX_IMAGE_SIZE_MB=5
UPLOAD_DIR=static/uploads
```

## Key Constraints

### Read-Only Fields
Trader CANNOT modify:
- Product price
- Central stock
- Categories
- Global product attributes

### Data Isolation
- Traders only see their own products, customers, orders
- Customers scoped to creating trader only
- Audit logs track all modifications

### Admin API Integration
Every sync request includes:
- `Authorization: Bearer <access_token>`
- `X-API-KEY: <trader_api_key>`

## Development

### Running Tests
```bash
pytest tests/
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Project Structure
```
app/
├── main.py              # FastAPI app
├── api/v1/              # API routes
├── services/            # Business logic
├── db/                  # Database models, session
├── core/                # Config, security, Admin client
├── schemas/             # Pydantic models
└── templates/           # Jinja2 HTML templates
```

## Deployment

### Docker
```bash
docker-compose up -d
```

### Production Settings
- Use environment-specific config
- Enable HTTPS
- Set strong JWT secret
- Use gunicorn + uvicorn workers
- Enable rate limiting
- Configure CORS for frontend domains

## API Examples

### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "secure_password_123",
    "business_name": "My Shop"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "secure_password_123"
  }'
```

### Sync Products
```bash
curl -X POST http://localhost:8000/api/v1/sync/products \
  -H "Authorization: Bearer <access_token>"
```

### List Products
```bash
curl -X GET http://localhost:8000/api/v1/trader/products \
  -H "Authorization: Bearer <access_token>"
```

### Update Product
```bash
curl -X PATCH http://localhost:8000/api/v1/trader/products/1 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "local_description": "Amazing product",
    "visibility": true
  }'
```

## Troubleshooting

### Database Connection Error
- Check PostgreSQL is running
- Verify DATABASE_URL in .env
- Run migrations: `alembic upgrade head`

### JWT Token Expired
- Use refresh token endpoint to get new access token
- Refresh tokens valid for 7 days

### Product Sync Failed
- Check ADMIN_API_BASE_URL is correct
- Verify trader status is ACTIVE
- Check Admin API is running and accessible

## Support

For issues or questions, check the project documentation or create an issue.
