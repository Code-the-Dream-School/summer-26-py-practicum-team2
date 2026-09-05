from __future__ import annotations

import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    pass


class City(Base):
    """Target locations from the city input contract (`cities.csv`)."""

    __tablename__ = "cities"

    city_id: Mapped[str] = mapped_column(Text, primary_key=True)
    city_name: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class GeocodingCache(Base):
    """Cache of geocoding results to avoid redundant API requests."""

    __tablename__ = "geocoding_cache"

    geocoding_query: Mapped[str] = mapped_column(Text, primary_key=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    country_code: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class PipelineRunStatus(str, enum.Enum):
    """Lifecycle states for a single pipeline execution."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PipelineRun(Base):
    """Tracks a single execution of the pipeline: window, status, and result counts."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    history_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[PipelineRunStatus] = mapped_column(
        SAEnum(PipelineRunStatus, name="pipeline_run_status", values_callable=lambda enum_cls: [member.value for member in enum_cls]),
        nullable=False,
        default=PipelineRunStatus.RUNNING,
    )
    city_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_response_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gold_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GoldAirQuality(Base):
    """One hourly air-quality row per city for the dashboard gold table."""

    __tablename__ = "gold_air_quality"
    __table_args__ = (
        UniqueConstraint("city_id", "observed_at", name="uq_gold_city_hour"),
        CheckConstraint("aqi >= 1 AND aqi <= 5", name="ck_gold_aqi"),
    )

    gold_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.city_id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aqi: Mapped[int] = mapped_column(Integer, nullable=False)
    co: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    no: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    no2: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    o3: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    so2: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    pm2_5: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    pm10: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    nh3: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RawResponse(Base):
    """Stores one raw OpenWeather response for a city and pipeline run."""

    __tablename__ = "raw_responses"
    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "pipeline_run_id",
            "window_start",
            "window_end",
            name="uq_raw_responses_city_run_window",
        ),
        CheckConstraint(
            "window_end > window_start",
            name="ck_raw_responses_valid_window",
        ),
    )

    raw_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    city_id: Mapped[str] = mapped_column(
        ForeignKey("cities.city_id"),
        nullable=False,
    )
    pipeline_run_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_runs.id"),
        nullable=False,
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    http_status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    raw_response: Mapped[dict | list | None] = mapped_column(
    JSON().with_variant(JSONB(), "postgresql"),
    nullable=True,
    )
    response_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )