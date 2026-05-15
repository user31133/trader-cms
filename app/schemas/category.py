from pydantic import BaseModel


class CategoryResponse(BaseModel):
    id: int
    source_id: int
    name: str

    class Config:
        from_attributes = True
