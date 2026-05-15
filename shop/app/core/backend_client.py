import logging
import httpx
from typing import Optional, List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class BackendClient:
    """HTTP client for communicating with the main backend API."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.ADMIN_API_BASE_URL
        self.client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client

    async def create_order(
        self,
        customer_email: str,
        trader_id: int,
        items: List[Dict[str, Any]],
        address: str,
        city: str,
        full_name: str,
        phone: str,
        access_token: Optional[str] = None
    ) -> dict:
        """
        Create order on backend.

        POST /api/v1/orders/customer
        {
          "customerEmail": "customer@example.com",
          "traderId": 1,
          "items": [{"productId": 1, "quantity": 2}],
          "address": "123 Main St",
          "city": "New York",
          "fullName": "John Doe",
          "phone": "555-1234"
        }

        Returns: {"orderId": 123, "status": "PENDING", "totalPrice": 99.99, "createdAt": "..."}
        """
        try:
            client = await self._get_client()
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            payload = {
                "customerEmail": customer_email,
                "traderId": trader_id,
                "items": [
                    {"productId": item["product_source_id"], "quantity": item["quantity"]}
                    for item in items
                ],
                "address": address,
                "city": city,
                "fullName": full_name,
                "phone": phone
            }

            logger.info(f"Creating order on backend for {customer_email}, trader {trader_id}")
            logger.debug(f"Order payload: {payload}")

            response = await client.post(
                f"{self.base_url}/api/v1/orders/customer",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Backend order created successfully: {result.get('orderId')}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Backend order creation failed with status {e.response.status_code}: {e.response.text}")
            raise Exception(f"Failed to create order on backend: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Backend order creation failed: {str(e)}")
            raise Exception(f"Failed to create order on backend: {str(e)}")

    async def get_product_stock(self, product_id: int) -> Optional[int]:
        """Get real-time stock for a product."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/v1/products/{product_id}")
            if response.status_code == 200:
                data = response.json()
                return data.get("stockQuantity")
            return None
        except Exception as e:
            logger.error(f"Failed to get product stock: {str(e)}")
            return None

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()


# Global instance
backend_client = BackendClient()
