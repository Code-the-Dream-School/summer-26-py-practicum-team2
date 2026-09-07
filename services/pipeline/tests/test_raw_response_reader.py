# services/pipeline/tests/test_raw_response_reader.py
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.models import Base, City, PipelineRun, PipelineRunStatus, RawResponse  # noqa: E402
from pipeline.transform.raw_response_reader import (  # noqa: E402
    flatten_raw_response,
    read_gold_ready_rows,
    read_raw_responses,
)


# SQLite maps BigInteger to BIGINT, and AUTOINCREMENT only works with an
# INTEGER PRIMARY KEY column. This override only applies when compiling for
# the sqlite dialect (used here for in-memory tests) — it does not affect
# how the real BigInteger column behaves against Postgres.
@compiles(BigInteger, "sqlite")
def _compile_big_integer_sqlite(type_, compiler, **kw):
    return "INTEGER"


SAMPLE_PAYLOAD = {
    "coord": [35.7796, -78.6382],
    "list": [
        {
            "dt": 1606482000,
            "main": {"aqi": 2},
            "components": {
                "co": 270.367, "no": 5.867, "no2": 43.184, "o3": 4.783,
                "so2": 14.544, "pm2_5": 13.448, "pm10": 15.524, "nh3": 0.289,
            },
        },
        {
            "dt": 1606485600,
            "main": {"aqi": 3},
            "components": {
                "co": 280.1, "no": 6.1, "no2": 44.0, "o3": 5.0,
                "so2": 15.0, "pm2_5": 14.0, "pm10": 16.0, "nh3": 0.3,
            },
        },
    ],
}


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _seed(engine) -> int:
    with Session(engine) as session:
        session.add(City(city_id="US_RAL_01", city_name="Raleigh", state="NC", country="US", is_active=True))
        run = PipelineRun(
            run_id="20260101T000000Z",
            source="openweather",
            history_hours=24,
            window_start_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
            window_end_utc=datetime(2026, 1, 2, tzinfo=timezone.utc),
            status=PipelineRunStatus.SUCCEEDED,
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        session.add(RawResponse(
            city_id="US_RAL_01",
            pipeline_run_id=run.id,
            window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            window_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
            http_status=200,
            raw_response=SAMPLE_PAYLOAD,
        ))
        session.commit()
        return run.id


def test_flatten_raw_response_produces_gold_ready_rows() -> None:
    fake_row = RawResponse(
        city_id="US_RAL_01",
        pipeline_run_id=1,
        window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
        http_status=200,
        raw_response=SAMPLE_PAYLOAD,
    )

    rows = flatten_raw_response(fake_row)

    assert len(rows) == 2
    assert rows[0] == {
        "city_id": "US_RAL_01",
        "observed_at": datetime(2020, 11, 27, 13, 0, tzinfo=timezone.utc),
        "aqi": 2,
        "co": 270.367, "no": 5.867, "no2": 43.184, "o3": 4.783,
        "so2": 14.544, "pm2_5": 13.448, "pm10": 15.524, "nh3": 0.289,
    }


def test_flatten_raw_response_skips_malformed_entries() -> None:
    bad_payload = {"list": [{"dt": 1606482000}]}  # missing main/components
    fake_row = RawResponse(
        city_id="US_RAL_01", pipeline_run_id=1,
        window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
        http_status=200, raw_response=bad_payload,
    )

    assert flatten_raw_response(fake_row) == []


def test_flatten_raw_response_handles_empty_payload() -> None:
    fake_row = RawResponse(
        city_id="US_RAL_01", pipeline_run_id=1,
        window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
        http_status=200, raw_response=None,
    )

    assert flatten_raw_response(fake_row) == []


def test_read_raw_responses_filters_by_city_and_run() -> None:
    engine = _engine()
    run_id = _seed(engine)

    by_city = read_raw_responses(city_id="US_RAL_01", engine=engine)
    by_run = read_raw_responses(pipeline_run_id=run_id, engine=engine)
    missing = read_raw_responses(city_id="GB_LON_01", engine=engine)

    assert len(by_city) == 1
    assert len(by_run) == 1
    assert missing == []


def test_read_gold_ready_rows_end_to_end() -> None:
    engine = _engine()
    _seed(engine)

    rows = read_gold_ready_rows(city_id="US_RAL_01", engine=engine)

    assert len(rows) == 2
    assert all(row["city_id"] == "US_RAL_01" for row in rows)
    assert {row["aqi"] for row in rows} == {2, 3}

def test_flatten_raw_response_skips_entries_with_invalid_types() -> None:
    bad_payload = {
        "list": [
            {"dt": "not-a-number", "main": {"aqi": 2}, "components": {}},
            {"dt": 1606482000, "main": {"aqi": "not-a-number"}, "components": {}},
            {"dt": 1606485600, "main": {"aqi": 3}, "components": {"co": "not-a-number"}},
        ]
    }
    fake_row = RawResponse(
        city_id="US_RAL_01", pipeline_run_id=1,
        window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
        http_status=200, raw_response=bad_payload,
    )

    assert flatten_raw_response(fake_row) == []


def test_flatten_raw_response_returns_empty_when_payload_is_not_a_dict() -> None:
    fake_row = RawResponse(
        city_id="US_RAL_01", pipeline_run_id=1,
        window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
        http_status=200, raw_response=["not", "a", "dict"],
    )

    assert flatten_raw_response(fake_row) == []