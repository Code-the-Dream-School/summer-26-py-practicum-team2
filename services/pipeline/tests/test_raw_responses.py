from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.raw_responses import (
    RawResponseRecord,
    prepare_raw_response_record,
    validate_raw_response_record,
)  # noqa: E402


def test_validate_raw_response_record_accepts_valid_record() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id="run_001",
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
        raw_response={"list": []},
    )

    validate_raw_response_record(record)


def test_validate_raw_response_record_rejects_empty_city_id() -> None:
    record = RawResponseRecord(
        city_id="   ",
        run_id="run_001",
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
    )

    with pytest.raises(ValueError, match="city_id is required"):
        validate_raw_response_record(record)


def test_validate_raw_response_record_rejects_invalid_window() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id="run_001",
        window_start=datetime(2026, 8, 2, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 1, tzinfo=timezone.utc),
        http_status=200,
    )

    with pytest.raises(ValueError, match="window_end must be later than window_start"):
        validate_raw_response_record(record)


def test_validate_raw_response_record_rejects_empty_run_id() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id="   ",
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
    )

    with pytest.raises(ValueError, match="run_id is required"):
        validate_raw_response_record(record)


def test_prepare_raw_response_record_returns_valid_record() -> None:
    record = RawResponseRecord(
        city_id="US_RAL_01",
        run_id="run_001",
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
        run_id="run_001",
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
        fetched_at=fetched_at,
    )

    prepared = prepare_raw_response_record(record)

    assert prepared.fetched_at == fetched_at

