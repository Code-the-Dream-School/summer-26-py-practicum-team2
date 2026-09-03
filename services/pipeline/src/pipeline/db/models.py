from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Text, Enum as SAEnum, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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


# Table: pipeline_runs — tracks each pipeline execution (window, status, result counts).
# id: internal PK.
# run_id: human-readable run identifier (timestamp), used to look up/update.
# source: data source for this run (e.g. "openweather").
# history_hours: hours of history covered.
# window_start_utc/window_end_utc: extraction time window.
# status: running | succeeded | failed.
# city_count/raw_response_count/gold_row_count: filled in as # the run progresses, null until known.
# error_message: set only on failure.
# started_at/finished_at: execution timespan.
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
        SAEnum(PipelineRunStatus, name="pipeline_run_status", values_callable=lambda enum_cls: [member.value for member in enum_cls],),
        nullable=False,
        default=PipelineRunStatus.RUNNING,
    )
    city_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_response_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gold_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
