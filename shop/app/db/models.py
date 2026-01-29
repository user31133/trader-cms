"""
Shop database models - imports from shared database via same connection.
Models are redefined here to avoid complex imports from trader-cms.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class ShopCustomer(Base):
    __tablename__ = "shop_customers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Trader(Base):
    __tablename__ = "traders"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=False)
    backend_user_id = Column(Integer, nullable=True, index=True)
    api_key = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(255), nullable=False)
    synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    central_stock = Column(Integer, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    version = Column(String(255), nullable=False)
    synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    category = relationship("Category", back_populates="products")
    trader_products = relationship("TraderProduct", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")


class TraderProduct(Base):
    __tablename__ = "trader_products"

    id = Column(Integer, primary_key=True, index=True)
    trader_id = Column(Integer, ForeignKey("traders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    local_description = Column(Text, nullable=True)
    local_notes = Column(Text, nullable=True)
    local_images = Column(JSON, default=list, nullable=False)
    visibility = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="trader_products")

    __table_args__ = (
        UniqueConstraint('trader_id', 'product_id'),
    )


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, unique=True, nullable=False, index=True)
    trader_id = Column(Integer, ForeignKey("traders.id"), nullable=False, index=True)
    customer_email = Column(String(255), nullable=True)
    total = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    version = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_snapshot = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


__all__ = [
    "ShopCustomer",
    "Product",
    "Category",
    "TraderProduct",
    "Order",
    "OrderItem",
    "Trader",
    "OrderStatus",
    "Base"
]
