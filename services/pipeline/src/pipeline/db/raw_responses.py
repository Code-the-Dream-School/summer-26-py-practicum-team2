from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from pipeline.db.models import RawResponse
from pipeline.db.session import get_engine

@dataclass(frozen=True)
class RawResponseRecord:
    city_id: str
    run_id: int
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

    if record.run_id <= 0:
        raise ValueError("run_id must be a positive integer")

    if record.window_end <= record.window_start:
        raise ValueError("window_end must be later than window_start")


def prepare_raw_response_record(record: RawResponseRecord) -> RawResponseRecord:
    validate_raw_response_record(record)

    if record.fetched_at is not None:
        return record

    return RawResponseRecord(
        city_id=record.city_id,
        run_id=record.run_id,
        window_start=record.window_start,
        window_end=record.window_end,
        http_status=record.http_status,
        raw_response=record.raw_response,
        response_text=record.response_text,
        error_message=record.error_message,
        fetched_at=datetime.now(timezone.utc),
    )


def raw_response_values(record: RawResponseRecord) -> dict[str, Any]:
    prepared = prepare_raw_response_record(record)

    return {
        "city_id": prepared.city_id,
        "pipeline_run_id": prepared.run_id,
        "pipeline_run_id": prepared.run_id,
        "window_start": prepared.window_start,
        "window_end": prepared.window_end,
        "http_status": prepared.http_status,
        "raw_response": prepared.raw_response,
        "response_text": prepared.response_text,
        "error_message": prepared.error_message,
        "fetched_at": prepared.fetched_at,
    }


def save_raw_response(
    record: RawResponseRecord,
    engine: Engine | None = None,
                    ) -> RawResponse:
    values = raw_response_values(record)
    db_engine = engine or get_engine()

    with Session(db_engine) as session:
        raw_response = RawResponse(**values)
        session.add(raw_response)
        session.commit()
        session.refresh(raw_response)

        return raw_response