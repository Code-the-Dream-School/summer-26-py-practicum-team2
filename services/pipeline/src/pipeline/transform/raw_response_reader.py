from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from pipeline.db.models import RawResponse
from pipeline.db.session import get_engine

POLLUTANT_FIELDS = ("co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3")


def read_raw_responses(
    *,
    city_id: str | None = None,
    pipeline_run_id: int | None = None,
    engine=None,
) -> list[RawResponse]:
    """Fetch raw_responses rows, optionally filtered by city and/or pipeline run."""
    resolved_engine = engine or get_engine()
    statement = select(RawResponse)
    if city_id is not None:
        statement = statement.where(RawResponse.city_id == city_id)
    if pipeline_run_id is not None:
        statement = statement.where(RawResponse.pipeline_run_id == pipeline_run_id)
    statement = statement.order_by(RawResponse.fetched_at)

    with Session(resolved_engine) as session:
        return list(session.scalars(statement).all())



def flatten_raw_response(raw_response_row: RawResponse) -> list[dict[str, Any]]:
    """Turn one raw_responses row's JSON payload into gold-ready row dicts.

    Returns one dict per hourly reading, already shaped for upsert_gold():
    {city_id, observed_at, aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3}.

    Returns an empty list if the payload isn't a dict, doesn't have a "list"
    key, or that key isn't a list. Within the list, entries that are missing
    expected fields or have values of the wrong type are skipped individually,
    not raised, so one bad reading doesn't fail the whole batch.
    """
    payload = raw_response_row.raw_response
    if not isinstance(payload, dict) or "list" not in payload:
        return []

    entries = payload["list"]
    if not isinstance(entries, list):
        return []

    rows: list[dict[str, Any]] = []
    for entry in entries:
        try:
            observed_at = datetime.fromtimestamp(int(entry["dt"]), tz=timezone.utc)
            aqi = int(entry["main"]["aqi"])
            components = entry.get("components", {})
            pollutants = {
                field: float(components[field]) if components.get(field) is not None else None
                for field in POLLUTANT_FIELDS
            }
        except (KeyError, TypeError, ValueError):
            continue

        rows.append({
            "city_id": raw_response_row.city_id,
            "observed_at": observed_at,
            "aqi": aqi,
            **pollutants,
        })

    return rows


def read_gold_ready_rows(
    *,
    city_id: str | None = None,
    pipeline_run_id: int | None = None,
    engine=None,
) -> list[dict[str, Any]]:
    """Read raw_responses and flatten them into gold-ready rows in one call."""
    raw_rows = read_raw_responses(city_id=city_id, pipeline_run_id=pipeline_run_id, engine=engine)
    result: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        result.extend(flatten_raw_response(raw_row))
    return result