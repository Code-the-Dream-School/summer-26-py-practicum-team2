from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.models import City, PipelineRun, PipelineRunStatus  # noqa: E402
from pipeline.db.raw_responses import (  # noqa: E402
    RawResponseRecord,
    prepare_raw_response_record,
    raw_response_values,
    save_raw_response,
    validate_raw_response_record,
)
from pipeline.db.session import get_engine  # noqa: E402

def test_validate_raw_response_record_accepts_valid_record() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id=1,
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
        raw_response={"list": []},
    )

    validate_raw_response_record(record)


def test_validate_raw_response_record_rejects_empty_city_id() -> None:
    record = RawResponseRecord(
        city_id="   ",
        run_id=1,
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
    )

    with pytest.raises(ValueError, match="city_id is required"):
        validate_raw_response_record(record)


def test_validate_raw_response_record_rejects_invalid_window() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id=1,
        window_start=datetime(2026, 8, 2, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 1, tzinfo=timezone.utc),
        http_status=200,
    )

    with pytest.raises(ValueError, match="window_end must be later than window_start"):
        validate_raw_response_record(record)


def test_validate_raw_response_record_rejects_non_positive_run_id() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id=0,
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
    )

    with pytest.raises(ValueError, match="run_id must be a positive integer"):
        validate_raw_response_record(record)


def test_prepare_raw_response_record_returns_valid_record() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id=1,
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
        raw_response={"list": []},
    )

    prepared = prepare_raw_response_record(record)

    assert prepared.city_id == record.city_id
    assert prepared.run_id == record.run_id
    assert prepared.raw_response == record.raw_response
    assert prepared.fetched_at is not None
    assert prepared.fetched_at.tzinfo is not None


def test_prepare_raw_response_record_preserves_fetched_at() -> None:
    fetched_at = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)

    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id=1,
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
        fetched_at=fetched_at,
    )

    prepared = prepare_raw_response_record(record)

    assert prepared.fetched_at == fetched_at


def test_raw_response_values_matches_storage_shape() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id=1,
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
        raw_response={"list": [{"dt": 123}]},
        response_text=None,
        error_message=None,
    )

    values = raw_response_values(record)

    assert values["city_id"] == "US_RAL_01"
    assert values["pipeline_run_id"] == 1
    assert values["http_status"] == 200
    assert values["raw_response"] == {"list": [{"dt": 123}]}
    assert values["fetched_at"] is not None


def test_raw_response_values_preserves_error_response() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id=2,
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=500,
        raw_response=None,
        response_text="Internal Server Error",
        error_message="OpenWeather request failed",
    )

    values = raw_response_values(record)

    assert values["http_status"] == 500
    assert values["raw_response"] is None
    assert values["response_text"] == "Internal Server Error"
    assert values["error_message"] == "OpenWeather request failed"


def test_save_raw_response_persists_record() -> None:
    engine = get_engine()
    test_run_id = f"run_test_{uuid4().hex}"

    with Session(engine) as session:
        session.merge(
            City(
                city_id="US_RAL_01",
                city_name="Raleigh",
                state="NC",
                country="US",
                is_active=True,
            )
        )

        pipeline_run = PipelineRun(
            run_id=test_run_id,
            source="openweather",
            history_hours=24,
            window_start_utc=datetime(2026, 8, 1, tzinfo=timezone.utc),
            window_end_utc=datetime(2026, 8, 2, tzinfo=timezone.utc),
            status=PipelineRunStatus.RUNNING,
            started_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        )
        session.add(pipeline_run)
        session.commit()
        session.refresh(pipeline_run)

    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id=pipeline_run.id,
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
        raw_response={"list": [{"dt": 123}]},
    )

    saved = save_raw_response(record, engine=engine)

    assert saved.raw_id is not None
    assert saved.city_id == "US_RAL_01"
    assert saved.pipeline_run_id == pipeline_run.id
