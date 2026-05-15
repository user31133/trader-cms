# Trader CMS

## Setup (from scratch)

### Step 1: Start Main Backend

```bash
cd online_shop-backend
docker compose up -d
```

Wait for backend to be ready at http://localhost:8081

### Step 2: Register Trader Account

```bash
curl -X POST http://localhost:8081/api/v1/auth/register-trader \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "yourpassword",
    "confirmPassword": "yourpassword",
    "fullName": "Your Shop Name"
  }'
```

Response:
```json
{
  "message": "Trader registration successful! Please verify OTP...",
  "user": { "id": 1, "email": "trader@example.com" },
  "isOtpRequired": true,
  "otpExpirationInSeconds": 300
}
```

Save `user.id` as your TRADER_ID.

### Step 3: Verify OTP

Check email/console for OTP code, then:

```bash
curl -X POST http://localhost:8081/api/v1/auth/login/otp \
  -H "Content-Type: application/json" \
  -d '{
    "username": "trader@example.com",
    "otp": "123456"
  }'
```

### Step 4: Wait for Admin Approval

Trader accounts require admin approval before login works.
Admin must approve via backend admin panel.

### Step 5: Configure CMS

```bash
cd trader-cms
cp .env.example .env
```

Edit `.env`:
```env
SHOP_NAME=YourShopName         # No spaces in name
TRADER_ID=1                    # CMS trader id (created after first login)
ADMIN_API_BASE_URL=http://shopbackend:8080  # Docker internal port

# Generate each secret:
# python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=your-generated-secret
SHOP_JWT_SECRET_KEY=your-generated-secret
SESSION_SECRET_KEY=your-generated-secret
```

> **Note**: Use port 8080 for Docker network (`shopbackend:8080`), port 8081 for host access (`localhost:8081`)

### Step 6: Start CMS & Shop

```bash
docker compose up --build
```

### Step 7: Login to CMS

1. Open http://localhost:8000
2. Login with trader email/password from Step 2
3. If OTP required, enter code from email
4. Sync products from main backend
5. Enable visibility for products to show in shop

### Step 8: Test Shop

1. Open http://localhost:8001
2. Browse products (only visible ones appear)
3. Register as customer
4. Add to cart, place order

## Access

| Service | URL |
|---------|-----|
| CMS | http://localhost:8000 |
| Shop | http://localhost:8001 |

## Important Notes

- **OTP Required**: All trader registrations require OTP verification
- **Admin Approval**: Traders cannot login until admin approves account
- **Product Visibility**: Products synced from backend are hidden by default - enable in CMS
- **Shared Database**: CMS and Shop share the same PostgreSQL database

## API Endpoints (Main Backend)

| Endpoint | Description |
|----------|-------------|
| POST /api/v1/auth/register-trader | Register trader (returns user.id) |
| POST /api/v1/auth/login/otp | Verify OTP |
| POST /api/v1/auth/login | Login (after approval) |
| GET /api/v1/admin/sync/products | Sync products (requires auth) |
| GET /api/v1/admin/sync/orders | Sync orders (requires auth) |
