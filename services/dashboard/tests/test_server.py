from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, insert
from sqlalchemy.pool import StaticPool

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

import server  # noqa: E402


NOW = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)


def _client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    server.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(server.cities),
            [
                {"city_id": "US_RAL_01", "city_name": "Raleigh", "state": "NC", "country": "US", "is_active": True},
                {"city_id": "GB_LON_01", "city_name": "London", "state": None, "country": "GB", "is_active": True},
                {"city_id": "US_NYC_99", "city_name": "New York", "state": "NY", "country": "US", "is_active": False},
            ],
        )
        connection.execute(
            insert(server.gold_air_quality),
            [
                {"gold_id": 1, "city_id": "US_RAL_01", "observed_at": NOW - timedelta(hours=3), "aqi": 2},
                {"gold_id": 2, "city_id": "US_RAL_01", "observed_at": NOW - timedelta(hours=1), "aqi": 4},
                {"gold_id": 3, "city_id": "US_RAL_01", "observed_at": NOW - timedelta(days=2), "aqi": 3},
                {"gold_id": 4, "city_id": "GB_LON_01", "observed_at": NOW - timedelta(hours=2), "aqi": 1},
                {"gold_id": 5, "city_id": "US_NYC_99", "observed_at": NOW - timedelta(hours=1), "aqi": 5},
            ],
        )
    return server.create_app(engine=engine, now_provider=lambda: NOW).test_client()


def test_cities_and_overview_only_include_active_cities_with_readings() -> None:
    client = _client()

    cities = client.get("/api/cities")
    overview = client.get("/api/cities/overview")

    assert cities.status_code == 200
    assert cities.json == [
        {"id": "GB_LON_01", "cityName": "London, GB"},
        {"id": "US_RAL_01", "cityName": "Raleigh, NC"},
    ]
    assert overview.status_code == 200
    assert overview.json[1]["aqi"] == 4
    assert overview.json[1]["observedAt"] == "2026-09-04T11:00:00+00:00"


def test_trend_uses_ordered_iso_timestamps() -> None:
    response = _client().get("/api/cities/US_RAL_01/trend")

    assert response.status_code == 200
    assert response.json["aqi"] == 4
    assert response.json["trend"] == [
        {"observedAt": "2026-09-04T09:00:00+00:00", "aqi": 2},
        {"observedAt": "2026-09-04T11:00:00+00:00", "aqi": 4},
    ]


def test_aggregates_validate_period_and_return_daily_values() -> None:
    client = _client()

    response = client.get("/api/cities/US_RAL_01/aggregates?period=daily")

    assert response.status_code == 200
    assert response.json == [
        {"date": "2026-09-02", "aqi": 3.0},
        {"date": "2026-09-04", "aqi": 3.0},
    ]
    assert client.get("/api/cities/US_RAL_01/aggregates?period=monthly").status_code == 400


def test_unknown_or_inactive_cities_are_not_exposed() -> None:
    client = _client()

    assert client.get("/api/cities/missing/trend").status_code == 404
    assert client.get("/api/cities/US_NYC_99/aggregates").status_code == 404
