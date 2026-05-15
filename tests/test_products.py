import pytest
from sqlalchemy import select

from app.db.models import Category, Product, TraderProduct
from app.services.product import update_trader_product, get_trader_products
from app.schemas.product import ProductUpdate


@pytest.mark.asyncio
async def test_update_product_description(db_session, active_trader):
    category = Category(source_id=1, name="Electronics", version="v1")
    db_session.add(category)
    await db_session.flush()

    product = Product(
        source_id=100,
        title="Test Product",
        price=99.99,
        central_stock=50,
        category_id=category.id,
        version="v1"
    )
    db_session.add(product)
    await db_session.flush()

    trader_product = TraderProduct(
        trader_id=active_trader.id,
        product_id=product.id,
        visibility=True
    )
    db_session.add(trader_product)
    await db_session.commit()

    update_data = ProductUpdate(
        local_description="Amazing product with great features"
    )

    result = await update_trader_product(db_session, active_trader.id, product.id, update_data)

    assert result.local_description == "Amazing product with great features"
    assert result.price == 99.99


@pytest.mark.asyncio
async def test_update_product_forbidden_price(db_session, active_trader):
    category = Category(source_id=2, name="Electronics", version="v1")
    db_session.add(category)
    await db_session.flush()

    product = Product(
        source_id=101,
        title="Test Product 2",
        price=99.99,
        central_stock=50,
        category_id=category.id,
        version="v1"
    )
    db_session.add(product)
    await db_session.flush()

    trader_product = TraderProduct(
        trader_id=active_trader.id,
        product_id=product.id
    )
    db_session.add(trader_product)
    await db_session.commit()

    update_data = ProductUpdate(price=50.00)

    with pytest.raises(ValueError, match="Cannot modify admin-controlled fields"):
        await update_trader_product(db_session, active_trader.id, product.id, update_data)


@pytest.mark.asyncio
async def test_update_product_forbidden_stock(db_session, active_trader):
    category = Category(source_id=3, name="Electronics", version="v1")
    db_session.add(category)
    await db_session.flush()

    product = Product(
        source_id=102,
        title="Test Product 3",
        price=99.99,
        central_stock=50,
        category_id=category.id,
        version="v1"
    )
    db_session.add(product)
    await db_session.flush()

    trader_product = TraderProduct(
        trader_id=active_trader.id,
        product_id=product.id
    )
    db_session.add(trader_product)
    await db_session.commit()

    update_data = ProductUpdate(central_stock=100)

    with pytest.raises(ValueError, match="Cannot modify admin-controlled fields"):
        await update_trader_product(db_session, active_trader.id, product.id, update_data)


@pytest.mark.asyncio
async def test_list_products(db_session, active_trader):
    category = Category(source_id=4, name="Accessories", version="v1")
    db_session.add(category)
    await db_session.flush()

    product = Product(
        source_id=103,
        title="USB Cable",
        price=9.99,
        central_stock=200,
        category_id=category.id,
        version="v1"
    )
    db_session.add(product)
    await db_session.flush()

    trader_product = TraderProduct(
        trader_id=active_trader.id,
        product_id=product.id,
        local_description="Quality cable",
        visibility=True,
        display_order=0
    )
    db_session.add(trader_product)
    await db_session.commit()

    products = await get_trader_products(db_session, active_trader.id)

    assert len(products) == 1
    assert products[0].title == "USB Cable"
    assert products[0].local_description == "Quality cable"
