"""Initial cities table.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-18
"""

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_schema"
down_revision: str | None = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("city_id", sa.Text(), nullable=False),
        sa.Column("city_name", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("city_id"),
    )


def downgrade() -> None:
    op.drop_table("cities")
