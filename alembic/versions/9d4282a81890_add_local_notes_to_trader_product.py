"""add_local_notes_to_trader_product

Revision ID: 9d4282a81890
Revises: e0d343a181b3
Create Date: 2026-01-13 19:03:36.667563

"""
from alembic import op
import sqlalchemy as sa


revision = '9d4282a81890'
down_revision = 'e0d343a181b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('trader_products', sa.Column('local_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('trader_products', 'local_notes')
