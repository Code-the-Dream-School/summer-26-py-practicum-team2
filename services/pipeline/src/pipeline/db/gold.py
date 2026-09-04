"""Load gold air-quality rows. Same city+hour updates; No duplicates could be inserted."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from pipeline.db.models import GoldAirQuality
from pipeline.db.session import get_engine

POLLUTANTS = ("co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3")


@dataclass(frozen=True)
class GoldUpsertResult:
    stored: int
    inserted: int
    updated: int


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _pollutant(row: dict, name: str) -> Decimal | None:
    value = row.get(name)
    if value is None:
        return None
    return Decimal(str(value))


def _apply_measurements(target: GoldAirQuality, row: dict) -> None:
    target.aqi = int(row["aqi"])
    for name in POLLUTANTS:
        setattr(target, name, _pollutant(row, name))


def upsert_gold(rows: list[dict], engine: Engine | None = None) -> GoldUpsertResult:
    """Insert gold rows, or update AQI and pollutants when city_id+observed_at already exist."""
    resolved_engine = engine or get_engine()
    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc)

    with Session(resolved_engine) as session:
        for row in rows:
            city_id = row["city_id"]
            observed_at = _as_utc(row["observed_at"])
            existing = session.scalar(
                select(GoldAirQuality).where(
                    GoldAirQuality.city_id == city_id,
                    GoldAirQuality.observed_at == observed_at,
                )
            )
            if existing is None:
                record = GoldAirQuality(
                    city_id=city_id,
                    observed_at=observed_at,
                    created_at=now,
                    updated_at=now,
                )
                _apply_measurements(record, row)
                session.add(record)
                inserted += 1
            else:
                _apply_measurements(existing, row)
                existing.updated_at = now
                updated += 1
        session.commit()

    return GoldUpsertResult(
        stored=inserted + updated,
        inserted=inserted,
        updated=updated,
    )


def count_gold_rows(engine: Engine | None = None) -> int:
    resolved_engine = engine or get_engine()
    with Session(resolved_engine) as session:
        return int(session.scalar(select(func.count()).select_from(GoldAirQuality)) or 0)
