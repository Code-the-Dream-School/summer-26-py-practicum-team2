from __future__ import annotations

import sys
from datetime import datetime, timezone
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

from pipeline.db.models import (  # noqa: E402
    Base,
    City,
    GoldAirQuality,
    PipelineRun,
    PipelineRunStatus,
    RawResponse,
)
from pipeline.transform.gold_transform import transform_and_load_gold  # noqa: E402


# SQLite maps BigInteger to BIGINT; AUTOINCREMENT needs INTEGER PRIMARY KEY.
# sqlite-only, same override used in test_raw_response_reader.py.
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


def _seed_run(engine) -> int:
    with Session(engine) as session:
        run = PipelineRun(
            run_id="test-transform",
            source="openweather",
            history_hours=24,
            window_start_utc=datetime(2026, 8, 1, tzinfo=timezone.utc),
            window_end_utc=datetime(2026, 8, 2, tzinfo=timezone.utc),
            status=PipelineRunStatus.RUNNING,
            started_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id


def _add_raw_response(engine, run_id: int, payload: dict, city_id: str = "US_RAL_01") -> None:
    with Session(engine) as session:
        session.add(
            RawResponse(
                city_id=city_id,
                pipeline_run_id=run_id,
                window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
                window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
                http_status=200,
                raw_response=payload,
            )
        )
        session.commit()


def test_transform_and_load_gold_reads_and_stores_valid_readings() -> None:
    engine = _engine()
    _seed_city(engine)
    run_id = _seed_run(engine)
    _add_raw_response(engine, run_id, {
        "list": [
            {"dt": 1606482000, "main": {"aqi": 2}, "components": {"pm2_5": 13.4}},
            {"dt": 1606485600, "main": {"aqi": 3}, "components": {"pm2_5": 14.0}},
        ]
    })

    result = transform_and_load_gold(pipeline_run_id=run_id, engine=engine)

    assert result.stored == 2
    assert result.inserted == 2
    with Session(engine) as session:
        assert session.scalar(select(GoldAirQuality).limit(1)) is not None


def test_transform_and_load_gold_with_no_raw_responses_stores_nothing() -> None:
    engine = _engine()
    _seed_city(engine)
    run_id = _seed_run(engine)

    result = transform_and_load_gold(pipeline_run_id=run_id, engine=engine)

    assert result.stored == 0
    assert result.inserted == 0
    assert result.updated == 0


def test_transform_and_load_gold_skips_malformed_entries_but_keeps_valid_ones() -> None:
    engine = _engine()
    _seed_city(engine)
    run_id = _seed_run(engine)
    _add_raw_response(engine, run_id, {
        "list": [
            {"dt": 1606482000, "main": {"aqi": 2}, "components": {"pm2_5": 13.4}},
            {"dt": "not-a-number", "main": {"aqi": 3}, "components": {}},
            {"main": {"aqi": 4}},
        ]
    })

    result = transform_and_load_gold(pipeline_run_id=run_id, engine=engine)

    assert result.stored == 1


def test_transform_and_load_gold_upserts_without_duplicating() -> None:
    engine = _engine()
    _seed_city(engine)
    run_id = _seed_run(engine)
    _add_raw_response(engine, run_id, {
        "list": [{"dt": 1606482000, "main": {"aqi": 2}, "components": {"pm2_5": 13.4}}]
    })

    first = transform_and_load_gold(pipeline_run_id=run_id, engine=engine)
    second = transform_and_load_gold(pipeline_run_id=run_id, engine=engine)

    assert first.inserted == 1
    assert second.inserted == 0
    assert second.updated == 1
    with Session(engine) as session:
        assert session.scalar(select(GoldAirQuality).limit(1)) is not None
        rows = session.scalars(select(GoldAirQuality)).all()
        assert len(rows) == 1


def test_transform_and_load_gold_propagates_upsert_errors() -> None:
    engine = _engine()
    _seed_city(engine)
    run_id = _seed_run(engine)
    _add_raw_response(engine, run_id, {
        "list": [{"dt": 1606482000, "main": {"aqi": 2}, "components": {}}]
    })

    with patch(
        "pipeline.transform.gold_transform.upsert_gold",
        side_effect=RuntimeError("simulated db failure"),
    ):
        with pytest.raises(RuntimeError, match="simulated db failure"):
            transform_and_load_gold(pipeline_run_id=run_id, engine=engine)