from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.raw_responses import RawResponseRecord, validate_raw_response_record  # noqa: E402


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
