"""Pipeline run tracking: create and update rows in the `pipeline_runs` table."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from pipeline.db.models import PipelineRun, PipelineRunStatus
from pipeline.db.session import get_engine


@dataclass(frozen=True)
class PipelineRunStatusUpdate:
    """Fields to apply when a run finishes or changes state."""

    status: str
    city_count: int | None = None
    raw_response_count: int | None = None
    gold_row_count: int | None = None
    error_message: str | None = None
    finished_at: datetime | None = None


def create_pipeline_run(
    run_id: str,
    source: str,
    history_hours: int,
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> int:
    """Insert a new pipeline_runs row with status=running and return its internal id."""
    with Session(get_engine()) as session:
        run = PipelineRun(
            run_id=run_id,
            source=source,
            history_hours=history_hours,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            status=PipelineRunStatus.RUNNING,
            started_at=datetime.now(window_start_utc.tzinfo),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id


def update_pipeline_run_status(run_id: str, update: PipelineRunStatusUpdate) -> None:
    """Apply status/result fields to the pipeline_runs row identified by run_id."""
    with Session(get_engine()) as session:
        run = session.query(PipelineRun).filter_by(run_id=run_id).one()
        run.status = PipelineRunStatus(update.status)
        if update.city_count is not None:
            run.city_count = update.city_count
        if update.raw_response_count is not None:
            run.raw_response_count = update.raw_response_count
        if update.gold_row_count is not None:
            run.gold_row_count = update.gold_row_count
        if update.error_message is not None:
            run.error_message = update.error_message
        if update.finished_at is not None:
            run.finished_at = update.finished_at
        session.commit()