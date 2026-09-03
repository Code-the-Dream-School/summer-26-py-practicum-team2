"""Add geocoding cache table.

Revision ID: 002_add_geocoding_cache
Revises: a00e2d059c17
Create Date: 2026-08-29
"""

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_geocoding_cache"
down_revision: str | None = "a00e2d059c17"


def upgrade() -> None:
    op.create_table(
        "geocoding_cache",
        sa.Column("geocoding_query", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("geocoding_query"),
    )


def downgrade() -> None:
    op.drop_table("geocoding_cache")
