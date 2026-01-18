import pytest

from app.services.customer import create_customer, list_customers
from app.schemas.customer import CustomerCreate


@pytest.mark.asyncio
async def test_create_customer(db_session, active_trader):
    data = CustomerCreate(
        email="customer@example.com",
        password="customer_password_123",
        full_name="John Doe",
        phone="1234567890"
    )

    customer = await create_customer(db_session, active_trader.id, data)

    assert customer.email == "customer@example.com"
    assert customer.full_name == "John Doe"
    assert customer.phone == "1234567890"


@pytest.mark.asyncio
async def test_create_customer_duplicate_email(db_session, active_trader):
    data1 = CustomerCreate(
        email="duplicate@example.com",
        password="password_123",
        full_name="First Customer"
    )

    await create_customer(db_session, active_trader.id, data1)

    data2 = CustomerCreate(
        email="duplicate@example.com",
        password="password_456",
        full_name="Second Customer"
    )

    with pytest.raises(ValueError, match="Email already exists"):
        await create_customer(db_session, active_trader.id, data2)


@pytest.mark.asyncio
async def test_list_customers(db_session, active_trader):
    customers_data = [
        CustomerCreate(
            email=f"customer{i}@example.com",
            password="password_123",
            full_name=f"Customer {i}"
        )
        for i in range(3)
    ]

    for data in customers_data:
        await create_customer(db_session, active_trader.id, data)

    customers = await list_customers(db_session, active_trader.id)

    assert len(customers) == 3
    assert customers[0].full_name == "Customer 0"
