"""add_version_to_orders

Revision ID: c7779b8d75ec
Revises: c0728c397468
Create Date: 2026-01-16 19:17:56.777959

"""
from alembic import op
import sqlalchemy as sa


revision = 'c7779b8d75ec'
down_revision = 'c0728c397468'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('version', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'version')
