"""add oauth mcp auth tables

Revision ID: 0004_oauth_mcp_auth
Revises: 0003_phone_login_location
Create Date: 2026-04-30
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_oauth_mcp_auth"
down_revision = "0003_phone_login_location"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("redirect_uris", sa.JSON(), nullable=False),
        sa.Column("grant_types", sa.JSON(), nullable=False),
        sa.Column("response_types", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "oauth_authorization_codes",
        sa.Column("code", sa.String(length=160), nullable=False),
        sa.Column("client_id", sa.String(length=80), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("code_challenge", sa.String(length=160), nullable=False),
        sa.Column("code_challenge_method", sa.String(length=16), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=255), nullable=True),
        sa.Column("resource", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["oauth_clients.id"]),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_index(
        op.f("ix_oauth_authorization_codes_client_id"),
        "oauth_authorization_codes",
        ["client_id"],
        unique=False,
    )
    op.create_table(
        "oauth_refresh_tokens",
        sa.Column("token", sa.String(length=160), nullable=False),
        sa.Column("client_id", sa.String(length=80), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=True),
        sa.Column("resource", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["oauth_clients.id"]),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index(op.f("ix_oauth_refresh_tokens_client_id"), "oauth_refresh_tokens", ["client_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_oauth_refresh_tokens_client_id"), table_name="oauth_refresh_tokens")
    op.drop_table("oauth_refresh_tokens")
    op.drop_index(op.f("ix_oauth_authorization_codes_client_id"), table_name="oauth_authorization_codes")
    op.drop_table("oauth_authorization_codes")
    op.drop_table("oauth_clients")
