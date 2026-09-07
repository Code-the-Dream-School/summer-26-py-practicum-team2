from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from pipeline.db.models import City
from pipeline.db.session import get_engine
from pipeline.extract.city_input import is_active_city, load_city_rows
from pipeline.extract.geocoding import GeocodingResult, geocode_city


@dataclass(frozen=True)
class CityImportResult:
    path: Path
    stored: int
    active: int
    inactive: int


def build_display_name(city_name: str, state: str | None, country: str) -> str:
    """Build the config-facing display name, e.g. "Raleigh, NC, US" or "London, GB"."""
    parts = [city_name]
    if state:
        parts.append(state)
    parts.append(country)
    return ", ".join(parts)


def city_from_row(row: dict[str, str], geo: GeocodingResult) -> City:
    return City(
        city_id=row["city_id"],
        display_name=build_display_name(row["city_name"], row.get("state") or None, row["country"]),
        geocode_cache_id=geo.cache_id,
        lat=geo.lat,
        lon=geo.lon,
        is_active=is_active_city(row),
    )


def upsert_cities(
    rows: list[dict[str, str]],
    engine: Engine | None = None,
    *,
    geocode_fn: Callable[..., GeocodingResult] = geocode_city,
) -> int:
    """Geocode and insert or update city records. Existing rows are matched by city_id.

    Geocoding happens here, once per import, per the schema design's decision that a
    city's coordinate is "locked in at config time" rather than re-resolved every run.
    """
    resolved_engine = engine or get_engine()
    with Session(resolved_engine) as session:
        for row in rows:
            geo = geocode_fn(
                raw_dir=None,
                city=row["city_name"],
                country_code=row["country"],
                state=row.get("state") or None,
                db_session=session,
            )
            session.merge(city_from_row(row, geo))
        session.commit()
    return len(rows)


def load_cities_from_db(
    engine: Engine | None = None, *, active_only: bool = True
) -> list[dict[str, str]]:
    """Return city records (city_id, display_name, lat, lon) from PostgreSQL."""
    resolved_engine = engine or get_engine()
    statement = select(City).order_by(City.city_id)
    if active_only:
        statement = statement.where(City.is_active.is_(True))

    with Session(resolved_engine) as session:
        cities = session.scalars(statement).all()
        return [
            {
                "city_id": city.city_id,
                "display_name": city.display_name,
                "lat": float(city.lat),
                "lon": float(city.lon),
                "is_active": city.is_active,
            }
            for city in cities
        ]


def import_cities(
    file_path: str | Path,
    engine: Engine | None = None,
    *,
    geocode_fn: Callable[..., GeocodingResult] = geocode_city,
) -> CityImportResult:
    """Validate a city CSV, geocode each row, and upsert every valid row into PostgreSQL."""
    path = Path(file_path)
    rows = load_city_rows(path, active_only=False)
    stored = upsert_cities(rows, engine, geocode_fn=geocode_fn)
    active = sum(1 for row in rows if is_active_city(row))
    return CityImportResult(
        path=path,
        stored=stored,
        active=active,
        inactive=stored - active,
    )
