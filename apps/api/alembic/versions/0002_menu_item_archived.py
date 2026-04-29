"""add archived flag to menu items

Revision ID: 0002_menu_item_archived
Revises: 0001_initial
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_menu_item_archived"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "menu_items",
        sa.Column("archived", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index(op.f("ix_menu_items_archived"), "menu_items", ["archived"], unique=False)
    if op.get_bind().dialect.name != "sqlite":
        op.alter_column("menu_items", "archived", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_menu_items_archived"), table_name="menu_items")
    op.drop_column("menu_items", "archived")
