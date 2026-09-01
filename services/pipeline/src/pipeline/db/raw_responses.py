from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RawResponseRecord:
    city_id: str
    run_id: str
    window_start: datetime
    window_end: datetime
    http_status: int
    raw_response: dict[str, Any] | list[Any] | None = None
    response_text: str | None = None
    error_message: str | None = None
    fetched_at: datetime | None = None


def validate_raw_response_record(record: RawResponseRecord) -> None:
    if not record.city_id.strip():
        raise ValueError("city_id is required")

    if not record.run_id.strip():
        raise ValueError("run_id is required")

    if record.window_end <= record.window_start:
        raise ValueError("window_end must be later than window_start")
