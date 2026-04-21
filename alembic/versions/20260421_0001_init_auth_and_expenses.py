"""create core tables and refresh tokens

Revision ID: 20260421_0001
Revises:
Create Date: 2026-04-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260421_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def _create_categories() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=True),
    )
    op.create_index("ix_categories_id", "categories", ["id"], unique=False)
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)


def _create_expenses() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_expenses_id", "expenses", ["id"], unique=False)
    op.create_index("ix_expenses_user_id", "expenses", ["user_id"], unique=False)
    op.create_index("ix_expenses_category_id", "expenses", ["category_id"], unique=False)


def _create_refresh_tokens() -> None:
    op.create_table(
        "user_refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_user_refresh_tokens_id",
        "user_refresh_tokens",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_user_refresh_tokens_user_id",
        "user_refresh_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_refresh_tokens_token_hash",
        "user_refresh_tokens",
        ["token_hash"],
        unique=True,
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("users"):
        _create_users()
    if not inspector.has_table("categories"):
        _create_categories()
    if not inspector.has_table("expenses"):
        _create_expenses()
    if not inspector.has_table("user_refresh_tokens"):
        _create_refresh_tokens()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("user_refresh_tokens"):
        op.drop_index("ix_user_refresh_tokens_token_hash", table_name="user_refresh_tokens")
        op.drop_index("ix_user_refresh_tokens_user_id", table_name="user_refresh_tokens")
        op.drop_index("ix_user_refresh_tokens_id", table_name="user_refresh_tokens")
        op.drop_table("user_refresh_tokens")
