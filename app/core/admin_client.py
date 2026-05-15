import logging
import httpx
from typing import Optional, Tuple
from datetime import datetime

from app.core.config import settings


def _flatten_categories(categories: list, parent_id=None) -> list:
    """Recursively flatten a nested category tree into a flat list."""
    result = []
    for cat in categories:
        result.append({"id": cat["id"], "name": cat["name"], "parentId": parent_id})
        for sub in cat.get("subcategories") or []:
            result.extend(_flatten_categories([sub], parent_id=cat["id"]))
    return result


def _map_product(p: dict, cat_lookup: dict) -> dict:
    """Map a ProductResponse from tradeops to the CMS internal format."""
    cat_id = p.get("categoryId") or 0
    return {
        "sourceId": p["id"],
        "title": p["name"],
        "price": float(p.get("basePrice") or 0),
        "centralStock": p.get("availableQty") or 0,
        "category": {
            "sourceId": cat_id,
            "name": cat_lookup.get(cat_id, str(cat_id)),
        },
        "version": f"v{p['id']}",
    }

logger = logging.getLogger(__name__)


class TokenExpiredError(Exception):
    """Raised when backend returns 401 - token needs refresh"""
    pass


class AdminAPIClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.ADMIN_API_BASE_URL
        self.client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client

    async def register_trader(self, email: str, business_name: str, password: str) -> dict:
        try:
            logger.info(f"Attempting to register trader: {email} at {self.base_url}/api/v1/auth/register-trader")
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/v1/auth/register-trader",
                json={
                    "email": email,
                    "fullName": business_name,
                    "password": password,
                    "confirmPassword": password
                }
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Backend registration successful for {email}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Backend registration failed with status {e.response.status_code}: {e.response.text}")
            raise Exception(f"Backend registration failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Backend registration failed: {str(e)}")
            raise Exception(f"Backend registration failed: {str(e)}")

    async def _fetch_categories_raw(self) -> list:
        """Fetch all categories from the backend, recursively flattened into a plain list."""
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/api/v1/admin/catalog/categories")
        response.raise_for_status()
        data = response.json()
        # Spring Page wraps items in 'content'; fall back to plain list
        items = data.get("content", data) if isinstance(data, dict) else data
        return _flatten_categories(items)

    async def sync_products(self, access_token: str, api_key: str, since: Optional[str] = None, page: int = 0) -> dict:
        try:
            client = await self._get_client()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": api_key,
            }
            params = {"traderId": settings.TRADER_ID, "page": page, "size": 20}

            logger.info(f"Syncing products from backend - page: {page}")
            response = await client.get(
                f"{self.base_url}/api/v1/catalog/products",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()


            # Fetch categories for name lookup
            cat_lookup: dict = {}
            try:
                cats = await self._fetch_categories_raw()
                cat_lookup = {c["id"]: c["name"] for c in cats}
            except Exception:
                pass

            products_list = data.get("content", [])
            logger.info(f"Product sync successful: {len(products_list)} products")
            return {
                "products": [
                    {
                        "sourceId": p["id"],
                        "title": p["name"],
                        "price": float(p.get("basePrice") or 0),
                        "centralStock": p.get("availableQty") or 0,
                        "categoryId": p.get("categoryId"),
                        "category": cat_lookup.get(p.get("categoryId"), str(p.get("categoryId", ""))),
                        # version encodes price+stock so any change triggers an update
                        "version": f"v{p['id']}-p{p.get('basePrice', 0)}-s{p.get('availableQty', 0)}",
                    }
                    for p in products_list
                ]
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("Product sync failed: Token expired")
                raise TokenExpiredError("Access token expired")
            if e.response.status_code == 403:
                logger.warning("Product sync failed: Trader not approved or invalid API key")
                raise Exception("Trader not approved or invalid API key")
            logger.error(f"Product sync failed with status {e.response.status_code}: {str(e)}")
            raise Exception(f"Failed to sync products: {str(e)}")
        except Exception as e:
            logger.error(f"Product sync failed: {str(e)}")
            raise Exception(f"Failed to sync products: {str(e)}")

    async def sync_orders(self, backend_user_id: int, access_token: str, api_key: str, since: Optional[str] = None, page: int = 0) -> dict:
        try:
            client = await self._get_client()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": api_key,
            }
            params = {"page": page, "size": 20}

            url = f"{self.base_url}/api/v1/trader/orders"
            logger.info(f"Syncing orders from backend - page: {page}")

            # TraderOrdersController uses @GetMapping with @RequestBody (non-standard).
            # httpx convenience .get() doesn't support json body; use .request() instead.
            response = await client.request(
                "GET",
                url,
                headers=headers,
                params=params,
                json={"traderId": settings.TRADER_ID},
            )

            if response.status_code != 200:
                logger.error(f"Order sync response status: {response.status_code}, body: {response.text[:200]}")

            response.raise_for_status()
            data = response.json()
            orders_list = data.get("content", [])
            logger.info(f"Order sync successful: {len(orders_list)} orders")


            return {
                "orders": [
                    {
                        # Use orderNumber as sourceId; fall back to index if missing
                        "sourceId": hash(order.get("orderNumber", str(i))) & 0x7FFFFFFF,
                        "customerEmail": "",
                        "totalPrice": order.get("totals", 0),
                        "status": order.get("status", "PENDING"),
                        "createdAt": order.get("createdAt", datetime.utcnow().isoformat()),
                        "city": "",
                        "address": order.get("deliveryAddress", ""),
                        "version": "",
                        "items": [],
                    }
                    for i, order in enumerate(orders_list)
                ]
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("Order sync failed: Token expired")
                raise TokenExpiredError("Access token expired")
            if e.response.status_code == 403:
                logger.warning("Order sync failed: Trader not approved or invalid API key")
                raise Exception("Trader not approved or invalid API key")
            logger.error(f"Order sync failed with status {e.response.status_code}: {str(e)}")
            raise Exception(f"Failed to sync orders: {str(e)}")
        except Exception as e:
            logger.error(f"Order sync failed: {str(e)}")
            raise Exception(f"Failed to sync orders: {str(e)}")

    async def browse_products(
        self,
        access_token: str,
        api_key: str,
        page: int = 0,
        limit: int = 20,
        category_id: Optional[int] = None,
        search: Optional[str] = None
    ) -> dict:
        try:
            client = await self._get_client()

            # Fetch categories for name lookup
            cat_lookup: dict = {}
            try:
                cats = await self._fetch_categories_raw()
                cat_lookup = {c["id"]: c["name"] for c in cats}
            except Exception:
                pass

            params: dict = {"traderId": settings.TRADER_ID, "page": page, "size": limit}
            if category_id:
                params["categoryId"] = category_id
            if search:
                params["query"] = search

            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            logger.info(f"Browsing products - page: {page}, category: {category_id}, search: {search}")
            response = await client.get(
                f"{self.base_url}/api/v1/catalog/products",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            products_list = data.get("content", [])
            products = [_map_product(p, cat_lookup) for p in products_list]

            return {
                "products": products,
                "total": data.get("totalElements", len(products)),
                "page": page,
                "totalPages": data.get("totalPages", 1),
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Browse products failed with status {e.response.status_code}: {str(e)}")
            raise Exception(f"Failed to browse products: {str(e)}")
        except Exception as e:
            logger.error(f"Browse products failed: {str(e)}")
            raise Exception(f"Failed to browse products: {str(e)}")


    async def browse_categories(self, access_token: str, api_key: str) -> dict:
        try:
            logger.info("Browsing categories from backend")
            cats = await self._fetch_categories_raw()
            return {"categories": [{"sourceId": c["id"], "name": c["name"], "parentId": c.get("parentId")} for c in cats]}
        except httpx.HTTPStatusError as e:
            logger.error(f"Browse categories failed with status {e.response.status_code}: {str(e)}")
            raise Exception(f"Failed to browse categories: {str(e)}")
        except Exception as e:
            logger.error(f"Browse categories failed: {str(e)}")
            raise Exception(f"Failed to browse categories: {str(e)}")

    async def update_allowed_categories(
        self,
        access_token: str,
        api_key: str,
        trader_id: int,
        category_ids: list[int],
    ) -> None:
        try:
            client = await self._get_client()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": api_key,
            }
            response = await client.put(
                f"{self.base_url}/api/v1/trader/{trader_id}/config/categories",
                headers=headers,
                json=category_ids,
            )
            if response.status_code == 401:
                raise TokenExpiredError("Backend token expired")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Update allowed categories failed with status {e.response.status_code}: {e.response.text}"
            )
            raise Exception(f"Failed to update allowed categories: {e.response.text}")

    async def get_products_by_category(
        self,
        access_token: str,
        api_key: str,
        category_id: int,
        page: int = 0,
        limit: int = 20
    ) -> dict:
        return await self.browse_products(
            access_token=access_token,
            api_key=api_key,
            page=page,
            limit=limit,
            category_id=category_id,
        )

    async def login_trader(self, email: str, password: str) -> dict:
        try:
            logger.info(f"Attempting backend login for: {email}")
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={
                    "username": email,
                    "password": password
                }
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Backend login response: isOtpRequired={result.get('isOtpRequired', False)}")
            return result
        except Exception as e:
            logger.error(f"Backend login failed: {str(e)}")
            raise Exception(f"Backend login failed: {str(e)}")

    async def verify_otp(self, email: str, otp: str) -> dict:
        try:
            logger.info(f"Attempting OTP verification for: {email}")
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/v1/auth/login/otp",
                json={
                    "username": email,
                    "otp": otp
                }
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"OTP verification successful for {email}")
            return result
        except Exception as e:
            logger.error(f"OTP verification failed: {str(e)}")
            raise Exception(f"OTP verification failed: {str(e)}")


    async def sync_products_with_refresh(
        self,
        access_token: str,
        refresh_token: str,
        api_key: str,
        since: Optional[str] = None,
        page: int = 0
    ) -> Tuple[dict, Optional[str], Optional[str]]:
        """
        Sync products with automatic token refresh on 401.
        Returns: (result, new_access_token, new_refresh_token)
        If tokens are None, no refresh was needed.
        """
        try:
            result = await self.sync_products(access_token, api_key, since, page)
            return result, None, None
        except TokenExpiredError:
            logger.info("Token expired during product sync, attempting refresh...")
            if not refresh_token:
                raise Exception("Token expired and no refresh token available")

            # Refresh the token
            new_tokens = await self.refresh_backend_token(refresh_token)
            new_access = new_tokens.get("accessToken")
            new_refresh = new_tokens.get("refreshToken", refresh_token)

            if not new_access:
                raise Exception("Token refresh failed - no new access token returned")

            # Retry with new token
            result = await self.sync_products(new_access, api_key, since, page)
            return result, new_access, new_refresh

    async def sync_orders_with_refresh(
        self,
        backend_user_id: int,
        access_token: str,
        refresh_token: str,
        api_key: str,
        since: Optional[str] = None,
        page: int = 0
    ) -> Tuple[dict, Optional[str], Optional[str]]:
        """
        Sync orders with automatic token refresh on 401.
        Returns: (result, new_access_token, new_refresh_token)
        If tokens are None, no refresh was needed.
        """
        try:
            result = await self.sync_orders(backend_user_id, access_token, api_key, since, page)
            return result, None, None
        except TokenExpiredError:
            logger.info("Token expired during order sync, attempting refresh...")
            if not refresh_token:
                raise Exception("Token expired and no refresh token available")

            # Refresh the token
            new_tokens = await self.refresh_backend_token(refresh_token)
            new_access = new_tokens.get("accessToken")
            new_refresh = new_tokens.get("refreshToken", refresh_token)

            if not new_access:
                raise Exception("Token refresh failed - no new access token returned")

            # Retry with new token
            result = await self.sync_orders(backend_user_id, new_access, api_key, since, page)
            return result, new_access, new_refresh

    async def refresh_backend_token(self, refresh_token: str) -> dict:
        try:
            logger.info(f"Attempting backend token refresh, token length: {len(refresh_token) if refresh_token else 0}")
            client = await self._get_client()
            payload = {"refreshToken": refresh_token}
            logger.debug(f"Refresh payload: {payload}")

            response = await client.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json=payload
            )

            logger.info(f"Backend refresh response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Backend refresh response body: {response.text}")

            response.raise_for_status()
            result = response.json()
            logger.info("Backend token refresh successful")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Backend token refresh HTTP error {e.response.status_code}: {e.response.text}")
            raise Exception(f"Backend token refresh failed: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Backend token refresh failed: {str(e)}")
            raise Exception(f"Backend token refresh failed: {str(e)}")


    async def close(self):
        if self.client:
            await self.client.aclose()


admin_client = AdminAPIClient()
