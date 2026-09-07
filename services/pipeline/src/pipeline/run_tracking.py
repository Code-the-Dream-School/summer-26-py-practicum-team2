"""Pipeline run tracking: create and update rows in the `pipeline_runs` table."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from pipeline.db.models import PipelineRun
from pipeline.db.session import get_engine

RUN_TYPES = ("geocode", "extract", "transform", "full")
STATUSES = ("running", "success", "failed", "partial")


@dataclass(frozen=True)
class PipelineRunStatusUpdate:
    """Fields to apply when a run finishes or changes state."""

    status: str
    city_count: int | None = None
    raw_response_count: int | None = None
    gold_row_count: int | None = None
    error_summary: str | None = None
    finished_at: datetime | None = None


def create_pipeline_run(
    *,
    run_type: str = "full",
    triggered_by: str | None = None,
    run_label: str | None = None,
    engine: Engine | None = None,
) -> int:
    """Insert a new pipeline_runs row with status='running' and return its run_id."""
    if run_type not in RUN_TYPES:
        raise ValueError(f"run_type must be one of {RUN_TYPES}, got {run_type!r}")

    resolved_engine = engine or get_engine()
    with Session(resolved_engine) as session:
        run = PipelineRun(
            run_type=run_type,
            status="running",
            started_at=datetime.now(timezone.utc),
            triggered_by=triggered_by,
            run_label=run_label,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.run_id


def update_pipeline_run_status(
    run_id: int, update: PipelineRunStatusUpdate, engine: Engine | None = None
) -> None:
    """Apply status/result fields to the pipeline_runs row identified by run_id."""
    if update.status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {update.status!r}")

    resolved_engine = engine or get_engine()
    with Session(resolved_engine) as session:
        run = session.get(PipelineRun, run_id)
        if run is None:
            raise ValueError(f"No pipeline_runs row with run_id={run_id}")
        run.status = update.status
        if update.city_count is not None:
            run.city_count = update.city_count
        if update.raw_response_count is not None:
            run.raw_response_count = update.raw_response_count
        if update.gold_row_count is not None:
            run.gold_row_count = update.gold_row_count
        if update.error_summary is not None:
            run.error_summary = update.error_summary
        if update.finished_at is not None:
            run.finished_at = update.finished_at
        session.commit()
