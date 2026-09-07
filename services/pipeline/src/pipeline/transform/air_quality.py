"""Transform stage: turns persisted raw OpenWeather responses into gold_air_quality rows.

Reads `raw_air_pollution_responses` (written by the extract stage) and produces the
rows `pipeline.load.gold.upsert_gold` expects, per `gold_table_contract.md` and
`city_air_tracker_schema_design.md` section 5. One malformed hourly entry inside a
raw response's `list` is skipped, not fatal to the whole batch — the same tolerance
the raw_response_contract calls for at the source-record level.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import Engine

from pipeline.load.gold import GoldUpsertResult, upsert_gold
from pipeline.db.models import RawAirPollutionResponse
from pipeline.extract.raw_responses import list_raw_responses_for_run

log = logging.getLogger(__name__)

POLLUTANT_FIELDS = ("co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3")


def _parse_entry(entry: dict) -> dict | None:
    try:
        observed_at = datetime.fromtimestamp(int(entry["dt"]), tz=timezone.utc)
        aqi = int(entry["main"]["aqi"])
    except (KeyError, TypeError, ValueError):
        return None

    components = entry.get("components") or {}
    row: dict = {"observed_at": observed_at, "aqi": aqi}
    for field in POLLUTANT_FIELDS:
        value = components.get(field)
        row[field] = None if value is None else value
    return row


def raw_response_to_gold_rows(raw: RawAirPollutionResponse) -> list[dict]:
    """Parse one raw response's `list` payload into gold-ready row dicts.

    Returns an empty list for a failed call (no payload) or a payload missing `list`.
    """
    if not raw.raw_response:
        return []

    entries = raw.raw_response.get("list") if isinstance(raw.raw_response, dict) else None
    if not entries:
        return []

    rows = []
    for entry in entries:
        parsed = _parse_entry(entry)
        if parsed is None:
            log.warning(
                "Skipping malformed air-quality entry for city_id=%s raw_id=%s",
                raw.city_id,
                raw.raw_id,
            )
            continue
        parsed["city_id"] = raw.city_id
        parsed["source_raw_id"] = raw.raw_id
        rows.append(parsed)
    return rows


def transform_raw_responses(raw_rows: list[RawAirPollutionResponse]) -> list[dict]:
    """Convert a batch of raw responses into gold rows, oldest fetch first.

    When two raw responses cover the same city+hour (e.g. a retried window), the row
    from the response fetched later wins, since `list_raw_responses_for_run` orders by
    `fetched_at` and `upsert_gold` applies rows in the order given.
    """
    gold_rows: list[dict] = []
    for raw in raw_rows:
        gold_rows.extend(raw_response_to_gold_rows(raw))
    return gold_rows


def run_transform_stage(run_id: int, engine: Engine | None = None) -> GoldUpsertResult:
    """Read every raw response for a pipeline run and upsert it into gold_air_quality."""
    raw_rows = list_raw_responses_for_run(run_id, engine=engine)
    gold_rows = transform_raw_responses(raw_rows)
    return upsert_gold(gold_rows, engine=engine)


__all__ = [
    "raw_response_to_gold_rows",
    "transform_raw_responses",
    "run_transform_stage",
]
