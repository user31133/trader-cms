from pydantic import BaseModel, EmailStr
from decimal import Decimal
from typing import List, Optional
from datetime import datetime


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    customer_email: EmailStr
    full_name: str
    phone: str
    address: str
    city: str


class OrderItemResponse(BaseModel):
    product_id: int
    product_title: str
    quantity: int
    price_snapshot: Decimal

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    source_id: Optional[int] = None
    customer_email: Optional[str]
    total: Decimal
    status: str
    created_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    limit: int
