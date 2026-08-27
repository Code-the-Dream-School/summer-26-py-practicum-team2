"""Tests for pipeline.run_tracking against a real Postgres database."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.models import PipelineRunStatus  # noqa: E402
from pipeline.run_tracking import (  # noqa: E402
    PipelineRunStatusUpdate,
    create_pipeline_run,
    update_pipeline_run_status,
)
from pipeline.db.session import get_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from pipeline.db.models import PipelineRun  # noqa: E402


def _unique_run_id() -> str:
    return f"test-{uuid.uuid4().hex[:12]}"


def test_create_pipeline_run_inserts_row_with_running_status() -> None:
    run_id = _unique_run_id()
    start = datetime.now(timezone.utc)
    end = start

    pipeline_run_id = create_pipeline_run(
        run_id=run_id,
        source="openweather",
        history_hours=24,
        window_start_utc=start,
        window_end_utc=end,
    )

    with Session(get_engine()) as session:
        run = session.get(PipelineRun, pipeline_run_id)
        assert run is not None
        assert run.run_id == run_id
        assert run.status == PipelineRunStatus.RUNNING
        assert run.finished_at is None


def test_update_pipeline_run_status_marks_run_succeeded() -> None:
    run_id = _unique_run_id()
    start = datetime.now(timezone.utc)
    pipeline_run_id = create_pipeline_run(
        run_id=run_id,
        source="openweather",
        history_hours=24,
        window_start_utc=start,
        window_end_utc=start,
    )
    finished = datetime.now(timezone.utc)

    update_pipeline_run_status(
        run_id,
        PipelineRunStatusUpdate(
            status="succeeded",
            city_count=3,
            raw_response_count=3,
            gold_row_count=72,
            finished_at=finished,
        ),
    )

    with Session(get_engine()) as session:
        run = session.get(PipelineRun, pipeline_run_id)
        assert run is not None
        assert run.status == PipelineRunStatus.SUCCEEDED
        assert run.city_count == 3
        assert run.gold_row_count == 72
        assert run.finished_at is not None


def test_update_pipeline_run_status_marks_run_failed_with_error() -> None:
    run_id = _unique_run_id()
    start = datetime.now(timezone.utc)
    create_pipeline_run(
        run_id=run_id,
        source="openweather",
        history_hours=24,
        window_start_utc=start,
        window_end_utc=start,
    )

    update_pipeline_run_status(
        run_id,
        PipelineRunStatusUpdate(status="failed", error_message="API timeout"),
    )

    with Session(get_engine()) as session:
        run = session.query(PipelineRun).filter_by(run_id=run_id).one()
        assert run.status == PipelineRunStatus.FAILED
        assert run.error_message == "API timeout"