from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Category
from app.schemas.category import CategoryResponse


async def list_categories(db: AsyncSession) -> list[CategoryResponse]:
    result = await db.execute(
        select(Category).order_by(Category.name)
    )
    categories = result.scalars().all()

    return [
        CategoryResponse(
            id=cat.id,
            source_id=cat.source_id,
            name=cat.name
        )
        for cat in categories
    ]
