"""Add gold_air_quality table.

Revision ID: 002_gold_air_quality
Revises: 002_add_geocoding_cache
Create Date: 2026-09-01
"""

import sqlalchemy as sa
from alembic import op

revision: str = "002_gold_air_quality"
down_revision: str | None = "002_add_geocoding_cache"


def upgrade() -> None:
    op.create_table(
        "gold_air_quality",
        sa.Column("gold_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("city_id", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aqi", sa.Integer(), nullable=False),
        sa.Column("co", sa.Numeric(), nullable=True),
        sa.Column("no", sa.Numeric(), nullable=True),
        sa.Column("no2", sa.Numeric(), nullable=True),
        sa.Column("o3", sa.Numeric(), nullable=True),
        sa.Column("so2", sa.Numeric(), nullable=True),
        sa.Column("pm2_5", sa.Numeric(), nullable=True),
        sa.Column("pm10", sa.Numeric(), nullable=True),
        sa.Column("nh3", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("gold_id"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.city_id"]),
        sa.UniqueConstraint("city_id", "observed_at", name="uq_gold_city_hour"),
        sa.CheckConstraint("aqi >= 1 AND aqi <= 5", name="ck_gold_aqi"),
    )


def downgrade() -> None:
    op.drop_table("gold_air_quality")
