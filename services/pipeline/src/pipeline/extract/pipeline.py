from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from pipeline.extract.air_pollution import AirQualityRecord, fetch_air_pollution_history
from pipeline.extract.geocoding import GeocodingNotFoundError, geocode_city

# Geocodes one city and fetch its recent air quality history. Returns None if the city cannot be geocoded.
def extract_city(
    city: dict[str, str],
    *,
    history_hours: int = 24,
    api_key: str | None = None,
    db_session: Session | None = None,
    now: datetime | None = None,
) -> dict | None:
   
    try:
        location = geocode_city(
            raw_dir=None,
            city=city["city_name"],
            country_code=city["country"],
            state=city.get("state") or None,
            api_key=api_key,
            db_session=db_session,
        )
    except GeocodingNotFoundError:
        return None

    end = now or datetime.now(timezone.utc)
    start = end - timedelta(hours=history_hours)
    records = fetch_air_pollution_history(
        lat=location.lat,
        lon=location.lon,
        start=start,
        end=end,
        api_key=api_key,
    )

    return {
        "city_id": city["city_id"],
        "city_name": location.name,
        "country": location.country_code,
        "lat": location.lat,
        "lon": location.lon,
        "records": records,
    }

# Extracts geocode + air quality history for each city, skipping ones that fail to geocode.
def extract_cities(
    cities: list[dict[str, str]],
    *,
    history_hours: int = 24,
    api_key: str | None = None,
    db_session: Session | None = None,
) -> list[dict]:

    results = [
        result
        for city in cities
        if (
            result := extract_city(
                city,
                history_hours=history_hours,
                api_key=api_key,
                db_session=db_session,
            )
        )
        is not None
    ]
    print(f"Extracted {len(results)}/{len(cities)} cities.")
    return results


__all__ = ["AirQualityRecord", "extract_city", "extract_cities"]
