from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


class OrderItemResponse(BaseModel):
    product_id: int
    product_title: str
    quantity: int
    price_snapshot: Decimal

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    source_id: int
    customer_email: Optional[str] = None
    total: Decimal
    status: str
    created_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


class OrderStats(BaseModel):
    total_orders: int
    total_revenue: Decimal
    pending_orders: int
