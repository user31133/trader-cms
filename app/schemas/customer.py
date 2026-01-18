from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class CustomerCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    phone: str = None


class CustomerResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str = None
    created_at: datetime

    class Config:
        from_attributes = True
