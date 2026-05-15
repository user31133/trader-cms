from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal


class ProductSyncItem(BaseModel):
    sourceId: int
    title: str
    price: Decimal
    centralStock: int
    category: str
    version: str


class ProductUpdate(BaseModel):
    local_description: Optional[str] = None
    local_notes: Optional[str] = None
    local_images: Optional[List[str]] = None
    visibility: Optional[bool] = None
    display_order: Optional[int] = None


class ProductResponse(BaseModel):
    id: int
    source_id: int
    title: str
    price: Decimal
    central_stock: int
    category_name: str
    local_description: Optional[str] = None
    local_notes: Optional[str] = None
    local_images: List[str] = []
    visibility: bool = True
    display_order: int = 0

    class Config:
        from_attributes = True
