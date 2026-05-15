from pydantic import BaseModel
from decimal import Decimal
from typing import List


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    product_id: int
    quantity: int


class CartItemResponse(BaseModel):
    product_id: int
    product_title: str
    product_price: Decimal
    quantity: int
    subtotal: Decimal


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total: Decimal
    item_count: int
