"""add_backend_user_id_to_trader

Revision ID: c0728c397468
Revises: 9d4282a81890
Create Date: 2026-01-13 19:12:07.766279

"""
from alembic import op
import sqlalchemy as sa


revision = 'c0728c397468'
down_revision = '9d4282a81890'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('traders', sa.Column('backend_user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_traders_backend_user_id'), 'traders', ['backend_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_traders_backend_user_id'), table_name='traders')
    op.drop_column('traders', 'backend_user_id')
