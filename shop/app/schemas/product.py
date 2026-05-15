from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


class CategoryResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    source_id: int
    title: str
    price: Decimal
    stock: int
    category: CategoryResponse
    local_description: Optional[str]
    local_notes: Optional[str]
    local_images: List[str]
    display_order: int

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    page: int
    limit: int
    total_pages: int
