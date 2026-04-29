"""add phone login and restaurant location

Revision ID: 0003_phone_login_location
Revises: 0002_menu_item_archived
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_phone_login_location"
down_revision = "0002_menu_item_archived"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("restaurants", sa.Column("location_text", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=40), nullable=True))
    op.execute("UPDATE users SET phone = COALESCE(NULLIF(email, ''), 'legacy-' || id) WHERE phone IS NULL")

    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("phone", existing_type=sa.String(length=40), nullable=False)
            batch_op.alter_column("email", existing_type=sa.String(length=255), nullable=True)
    else:
        op.alter_column("users", "phone", existing_type=sa.String(length=40), nullable=False)
        op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)

    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    if op.get_bind().dialect.name == "sqlite":
        op.execute("UPDATE users SET email = phone || '@legacy.local' WHERE email IS NULL")
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("email", existing_type=sa.String(length=255), nullable=False)
            batch_op.drop_column("phone")
    else:
        op.execute("UPDATE users SET email = phone || '@legacy.local' WHERE email IS NULL")
        op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
        op.drop_column("users", "phone")
    op.drop_column("restaurants", "location_text")
