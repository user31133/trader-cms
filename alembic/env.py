import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from alembic import context
from app.core.config import settings
from app.db.base import Base
from app.db.models import (
    Trader,
    Category,
    Product,
    TraderProduct,
    Order,
    OrderItem,
    AuditLog
)


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sqlalchemy_url() -> URL:
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    sqlalchemy_url = get_sqlalchemy_url()
    context.configure(
        url=sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_sqlalchemy_url()

    connectable = create_async_engine(
        get_sqlalchemy_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
