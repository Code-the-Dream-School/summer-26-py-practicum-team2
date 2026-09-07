from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.models import Base, City, PipelineRun, PipelineRunStatus  # noqa: E402
from pipeline.orchestration import flow as flow_module  # noqa: E402


@compiles(BigInteger, "sqlite")
def _compile_big_integer_sqlite(type_, compiler, **kw):
    return "INTEGER"


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _seed_city(engine, city_id: str = "US_RAL_01") -> None:
    with Session(engine) as session:
        session.merge(
            City(city_id=city_id, city_name="Raleigh", state="NC", country="US", is_active=True)
        )
        session.commit()


def test_flow_marks_run_failed_when_transform_stage_raises() -> None:
    engine = _engine()
    _seed_city(engine)

    with (
        patch.object(
            flow_module,
            "load_cities_task",
            return_value=[{"city_id": "US_RAL_01", "city_name": "Raleigh", "state": "NC", "country": "US"}],
        ),
        patch.object(flow_module, "extract_task", return_value=[]),
        patch.object(
            flow_module,
            "transform_and_load_task",
            side_effect=RuntimeError("simulated transform failure"),
        ),
    ):
        with pytest.raises(RuntimeError, match="simulated transform failure"):
            flow_module.run_pipeline_flow(history_hours=24, engine=engine)

    with Session(engine) as session:
        run = session.scalars(
            select(PipelineRun).order_by(PipelineRun.started_at.desc())
        ).first()
        assert run is not None
        assert run.status == PipelineRunStatus.FAILED
        assert run.error_message == "simulated transform failure"


def test_flow_marks_run_succeeded_and_records_gold_row_count() -> None:
    engine = _engine()
    _seed_city(engine)

    with (
        patch.object(
            flow_module,
            "load_cities_task",
            return_value=[{"city_id": "US_RAL_01", "city_name": "Raleigh", "state": "NC", "country": "US"}],
        ),
        patch.object(flow_module, "extract_task", return_value=[{"city_id": "US_RAL_01"}]),
        patch.object(flow_module, "transform_and_load_task", return_value=5),
    ):
        flow_module.run_pipeline_flow(history_hours=24, engine=engine)

    with Session(engine) as session:
        run = session.scalars(
            select(PipelineRun).order_by(PipelineRun.started_at.desc())
        ).first()
        assert run is not None
        assert run.status == PipelineRunStatus.SUCCEEDED
        assert run.gold_row_count == 5
        assert run.city_count == 1
        assert run.raw_response_count == 1