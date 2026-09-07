from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    pass


_JSONB_TYPE = JSON().with_variant(JSONB(), "postgresql")
# SQLite only auto-increments a column stored as its "INTEGER PRIMARY KEY" rowid
# alias; a BigInteger PK is left NULL on insert under SQLite otherwise. Postgres gets
# a real bigserial; SQLite-backed unit tests get a plain autoincrementing integer.
_BIGINT_PK = BigInteger().with_variant(Integer(), "sqlite")


class GeocodingCache(Base):
    """Caches OpenWeather Geocoding API lookups so a city isn't re-geocoded every run.

    Mirrors `city_air_tracker_schema_design.md` section 1. Overwrite-on-refresh is a
    deliberate decision (see the design doc); there is no history of prior lat/lon per query.
    """

    __tablename__ = "geocoding_cache"

    cache_id: Mapped[int] = mapped_column(_BIGINT_PK, primary_key=True, autoincrement=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    resolved_name: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_country: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    lon: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    raw_response: Mapped[dict | list] = mapped_column(_JSONB_TYPE, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class City(Base):
    """Canonical, pipeline-tracked city list with a resolved coordinate locked at config time.

    Mirrors `city_air_tracker_schema_design.md` section 2. lat/lon are a deliberate
    denormalized copy of geocoding_cache, locked in when the city is imported, so the
    pipeline has a stable coordinate to call the history endpoint even if the cache
    entry is later refreshed or purged.
    """

    __tablename__ = "cities"
    # `uq_cities_coords`, a functional unique index on ROUND(lat,4)/ROUND(lon,4), is
    # Postgres-only syntax (see the design doc) and is created by the Alembic migration
    # instead of here, so SQLite-backed unit tests can still create this table.

    city_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    geocode_cache_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("geocoding_cache.cache_id", ondelete="SET NULL"),
        nullable=True,
    )
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    lon: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class PipelineRun(Base):
    """One row per ETL execution (geocode, extract, transform, or full), for monitoring/lineage.

    Mirrors `city_air_tracker_schema_design.md` section 3, plus additive (non-conflicting)
    bookkeeping columns (`city_count`, `raw_response_count`, `gold_row_count`, `run_label`)
    that the design doc doesn't mention but doesn't prohibit either.
    """

    __tablename__ = "pipeline_runs"
    __table_args__ = (
        CheckConstraint(
            "run_type IN ('geocode','extract','transform','full')",
            name="ck_pipeline_runs_run_type",
        ),
        CheckConstraint(
            "status IN ('running','success','failed','partial')",
            name="ck_pipeline_runs_status",
        ),
    )

    run_id: Mapped[int] = mapped_column(_BIGINT_PK, primary_key=True, autoincrement=True)
    run_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additive bookkeeping, not part of the design doc's minimal column list.
    run_label: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    city_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_response_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gold_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RawAirPollutionResponse(Base):
    """Append-only log of every history-endpoint call attempt, including failed ones.

    Mirrors `city_air_tracker_schema_design.md` section 4. This is the audit trail and
    replay source if transform logic ever changes; one row per API call, not per hourly
    reading (see the design doc's judgment call #3).
    """

    __tablename__ = "raw_air_pollution_responses"
    __table_args__ = (
        UniqueConstraint(
            "city_id", "run_id", "window_start", "window_end", name="uq_raw_run_window"
        ),
        CheckConstraint("window_end > window_start", name="ck_raw_window"),
    )

    raw_id: Mapped[int] = mapped_column(_BIGINT_PK, primary_key=True, autoincrement=True)
    city_id: Mapped[str] = mapped_column(
        ForeignKey("cities.city_id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_runs.run_id", ondelete="RESTRICT"), nullable=False
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_response: Mapped[dict | list | None] = mapped_column(_JSONB_TYPE, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class GoldAirQuality(Base):
    """One row per city per hour: the deduplicated, transformed dataset the dashboard reads.

    Mirrors `city_air_tracker_schema_design.md` section 5, including `source_raw_id`
    lineage back to the raw response that produced the row.
    """

    __tablename__ = "gold_air_quality"
    __table_args__ = (
        UniqueConstraint("city_id", "observed_at", name="uq_gold_city_hour"),
        CheckConstraint("aqi >= 1 AND aqi <= 5", name="ck_gold_aqi"),
    )

    gold_id: Mapped[int] = mapped_column(_BIGINT_PK, primary_key=True, autoincrement=True)
    city_id: Mapped[str] = mapped_column(
        ForeignKey("cities.city_id", ondelete="RESTRICT"), nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aqi: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    co: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    no: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    no2: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    o3: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    so2: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    pm2_5: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    pm10: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    nh3: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    source_raw_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("raw_air_pollution_responses.raw_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
