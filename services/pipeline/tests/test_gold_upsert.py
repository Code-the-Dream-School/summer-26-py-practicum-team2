from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.gold import upsert_gold  # noqa: E402
from pipeline.db.models import Base, City, GoldAirQuality  # noqa: E402


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _seed_city(engine) -> None:
    with Session(engine) as session:
        session.add(
            City(
                city_id="US_RAL_01",
                city_name="Raleigh",
                state="NC",
                country="US",
                is_active=True,
            )
        )
        session.commit()


def _hour(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def test_upsert_gold_inserts_sample_rows_without_duplicates() -> None:
    engine = _engine()
    _seed_city(engine)
    noon = _hour(2026, 8, 31, 12)
    one_pm = _hour(2026, 8, 31, 13)

    first = upsert_gold(
        [
            {"city_id": "US_RAL_01", "observed_at": noon, "aqi": 2, "pm2_5": 8.1},
            {"city_id": "US_RAL_01", "observed_at": one_pm, "aqi": 3, "pm2_5": 12.4},
        ],
        engine=engine,
    )

    assert first.inserted == 2
    assert first.updated == 0

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(GoldAirQuality)) == 2


def test_upsert_gold_updates_same_city_hour_and_does_not_double_count() -> None:
    engine = _engine()
    _seed_city(engine)
    noon = _hour(2026, 8, 31, 12)
    rows = [
        {"city_id": "US_RAL_01", "observed_at": noon, "aqi": 2, "pm2_5": 8.1, "no2": 11.0}
    ]

    upsert_gold(rows, engine=engine)
    second = upsert_gold(
        [
            {
                "city_id": "US_RAL_01",
                "observed_at": noon,
                "aqi": 4,
                "pm2_5": 20.5,
                "no2": 15.2,
            }
        ],
        engine=engine,
    )

    assert second.inserted == 0
    assert second.updated == 1

    with Session(engine) as session:
        stored = session.scalars(select(GoldAirQuality)).all()
        assert len(stored) == 1
        row = stored[0]
        assert row.aqi == 4
        assert row.pm2_5 == Decimal("20.5")
        assert row.no2 == Decimal("15.2")
        assert row.updated_at is not None
