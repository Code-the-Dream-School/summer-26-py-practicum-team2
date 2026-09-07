"""Align cities, geocoding_cache, pipeline_runs, raw responses, and gold with
city_air_tracker_schema_design.md (the schema design doc, treated as the source of
truth per team decision).

This is a breaking rebuild of the affected tables rather than a column-by-column
ALTER migration: `cities` drops city_name/state/country in favor of display_name +
locked-in lat/lon, `pipeline_runs` is restructured around the design's run_type/status
vocabulary, `raw_responses` is renamed to `raw_air_pollution_responses`, and
`gold_air_quality` gains `source_raw_id` lineage. There is no production data to
migrate forward (local/dev project), so tables are dropped and recreated in FK-safe
order instead of carrying legacy rows through renamed/retyped columns.

Revision ID: 003_align_schema_design
Revises: ec47af133e82
Create Date: 2026-09-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_align_schema_design"
down_revision: str | None = "ec47af133e82"


def upgrade() -> None:
    # Drop children before parents.
    op.drop_table("gold_air_quality")
    op.drop_table("raw_responses")
    op.drop_table("pipeline_runs")
    op.drop_table("cities")
    op.drop_table("geocoding_cache")
    op.execute("DROP TYPE IF EXISTS pipeline_run_status")

    op.create_table(
        "geocoding_cache",
        sa.Column("cache_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("resolved_name", sa.Text(), nullable=False),
        sa.Column("resolved_country", sa.Text(), nullable=False),
        sa.Column("resolved_state", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("cache_id"),
        sa.UniqueConstraint("query_text", name="uq_geocoding_query"),
    )

    op.create_table(
        "cities",
        sa.Column("city_id", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("geocode_cache_id", sa.BigInteger(), nullable=True),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("city_id"),
        sa.UniqueConstraint("display_name", name="uq_cities_display_name"),
        sa.ForeignKeyConstraint(
            ["geocode_cache_id"], ["geocoding_cache.cache_id"], ondelete="SET NULL"
        ),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_cities_coords ON cities "
        "(ROUND(lat::numeric, 4), ROUND(lon::numeric, 4))"
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("run_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by", sa.Text(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("run_label", sa.Text(), nullable=True),
        sa.Column("city_count", sa.Integer(), nullable=True),
        sa.Column("raw_response_count", sa.Integer(), nullable=True),
        sa.Column("gold_row_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint("run_label"),
        sa.CheckConstraint(
            "run_type IN ('geocode','extract','transform','full')",
            name="ck_pipeline_runs_run_type",
        ),
        sa.CheckConstraint(
            "status IN ('running','success','failed','partial')",
            name="ck_pipeline_runs_status",
        ),
    )

    op.create_table(
        "raw_air_pollution_responses",
        sa.Column("raw_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("city_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("window_end > window_start", name="ck_raw_window"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.city_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.run_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("raw_id"),
        sa.UniqueConstraint(
            "city_id", "run_id", "window_start", "window_end", name="uq_raw_run_window"
        ),
    )

    op.create_table(
        "gold_air_quality",
        sa.Column("gold_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("city_id", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aqi", sa.SmallInteger(), nullable=False),
        sa.Column("co", sa.Numeric(), nullable=True),
        sa.Column("no", sa.Numeric(), nullable=True),
        sa.Column("no2", sa.Numeric(), nullable=True),
        sa.Column("o3", sa.Numeric(), nullable=True),
        sa.Column("so2", sa.Numeric(), nullable=True),
        sa.Column("pm2_5", sa.Numeric(), nullable=True),
        sa.Column("pm10", sa.Numeric(), nullable=True),
        sa.Column("nh3", sa.Numeric(), nullable=True),
        sa.Column("source_raw_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("gold_id"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.city_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_raw_id"], ["raw_air_pollution_responses.raw_id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("city_id", "observed_at", name="uq_gold_city_hour"),
        sa.CheckConstraint("aqi >= 1 AND aqi <= 5", name="ck_gold_aqi"),
    )


def downgrade() -> None:
    raise NotImplementedError(
        "003_align_schema_design is a breaking rebuild; restore from a pre-migration "
        "backup instead of downgrading."
    )
