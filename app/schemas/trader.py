from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class TraderProfileResponse(BaseModel):
    id: int
    email: EmailStr
    business_name: str
    backend_user_id: Optional[int] = None
    api_key: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TraderProfileUpdate(BaseModel):
    business_name: Optional[str] = None
