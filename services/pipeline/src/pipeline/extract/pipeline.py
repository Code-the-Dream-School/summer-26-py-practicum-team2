from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine

from pipeline.extract.raw_responses import RawResponseRecord, save_raw_response
from pipeline.db.models import RawAirPollutionResponse
from pipeline.extract.air_pollution import (
    AirPollutionConfigError,
    AirPollutionError,
    fetch_air_pollution_history_raw,
)


# Fetches one city's raw air-quality history and persists it to raw_air_pollution_responses.
# Coordinates come from the cities table (locked in at geocode/import time), so this stage
# never re-geocodes. A failed request is still logged, per the raw-response audit contract.
def extract_city(
    city: dict[str, str],
    *,
    window_start: datetime,
    window_end: datetime,
    run_id: int,
    api_key: str | None = None,
    engine: Engine | None = None,
) -> RawAirPollutionResponse:
    try:
        payload, status = fetch_air_pollution_history_raw(
            lat=float(city["lat"]),
            lon=float(city["lon"]),
            start=window_start,
            end=window_end,
            api_key=api_key,
        )
        record = RawResponseRecord(
            city_id=city["city_id"],
            run_id=run_id,
            window_start=window_start,
            window_end=window_end,
            http_status=status,
            raw_response=payload,
        )
    except AirPollutionConfigError:
        raise
    except AirPollutionError as exc:
        record = RawResponseRecord(
            city_id=city["city_id"],
            run_id=run_id,
            window_start=window_start,
            window_end=window_end,
            http_status=0,
            error_message=str(exc),
        )

    return save_raw_response(record, engine=engine)


# Extracts and persists raw air-quality history for every city.
def extract_cities(
    cities: list[dict[str, str]],
    *,
    window_start: datetime,
    window_end: datetime,
    run_id: int,
    api_key: str | None = None,
    engine: Engine | None = None,
) -> list[RawAirPollutionResponse]:
    results = [
        extract_city(
            city,
            window_start=window_start,
            window_end=window_end,
            run_id=run_id,
            api_key=api_key,
            engine=engine,
        )
        for city in cities
    ]
    print(f"Extracted {len(results)}/{len(cities)} cities.")
    return results


__all__ = ["extract_city", "extract_cities"]
