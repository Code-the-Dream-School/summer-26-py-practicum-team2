from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from pipeline.db.models import City
from pipeline.db.session import get_engine
from pipeline.extract.city_input import is_active_city, load_city_rows


@dataclass(frozen=True)
class CityImportResult:
    path: Path
    stored: int
    active: int
    inactive: int


def city_from_row(row: dict[str, str]) -> City:
    state = (row.get("state") or "").strip() or None
    return City(
        city_id=row["city_id"],
        city_name=row["city_name"],
        state=state,
        country=row["country"],
        is_active=is_active_city(row),
    )


def city_to_row(city: City) -> dict[str, str]:
    return {
        "city_id": city.city_id,
        "city_name": city.city_name,
        "state": city.state or "",
        "country": city.country,
        "is_active": "TRUE" if city.is_active else "FALSE",
    }


def upsert_cities(rows: list[dict[str, str]], engine: Engine | None = None) -> int:
    """Insert or update city records. Existing rows are matched by city_id."""
    resolved_engine = engine or get_engine()
    with Session(resolved_engine) as session:
        for row in rows:
            session.merge(city_from_row(row))
        session.commit()
    return len(rows)


def load_cities_from_db(
    engine: Engine | None = None, *, active_only: bool = True
) -> list[dict[str, str]]:
    """Return city records from PostgreSQL"""
    resolved_engine = engine or get_engine()
    statement = select(City).order_by(City.city_id)
    if active_only:
        statement = statement.where(City.is_active.is_(True))

    with Session(resolved_engine) as session:
        cities = session.scalars(statement).all()
        return [city_to_row(city) for city in cities]


def import_cities(file_path: str | Path, engine: Engine | None = None) -> CityImportResult:
    """Validate a city CSV and upsert every valid row into PostgreSQL."""
    path = Path(file_path)
    rows = load_city_rows(path, active_only=False)
    stored = upsert_cities(rows, engine=engine)
    active = sum(1 for row in rows if is_active_city(row))
    return CityImportResult(
        path=path,
        stored=stored,
        active=active,
        inactive=stored - active,
    )
