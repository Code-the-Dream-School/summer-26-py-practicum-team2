"""Flask API serving dashboard data from the pipeline's PostgreSQL tables."""

from __future__ import annotations

import os
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

metadata = MetaData()
cities = Table(
    "cities", metadata,
    Column("city_id", String, primary_key=True),
    Column("city_name", String, nullable=False),
    Column("state", String),
    Column("country", String, nullable=False),
    Column("is_active", Boolean, nullable=False),
)
gold_air_quality = Table(
    "gold_air_quality", metadata,
    Column("gold_id", Integer, primary_key=True),
    Column("city_id", String, nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("aqi", Integer, nullable=False),
)


def _get_engine() -> Engine:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and start Postgres.")
    return create_engine(database_url, pool_pre_ping=True)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _city_label(city_name: str, state: str | None, country: str) -> str:
    return f"{city_name}, {state or country}"


def _city_rows(engine: Engine):
    latest_reading = (
        select(
            gold_air_quality.c.city_id,
            gold_air_quality.c.observed_at,
            gold_air_quality.c.aqi,
            func.row_number().over(
                partition_by=gold_air_quality.c.city_id,
                order_by=gold_air_quality.c.observed_at.desc(),
            ).label("reading_rank"),
        ).subquery()
    )
    statement = (
        select(
            cities.c.city_id, cities.c.city_name, cities.c.state, cities.c.country,
            latest_reading.c.observed_at, latest_reading.c.aqi,
        )
        .join(latest_reading, latest_reading.c.city_id == cities.c.city_id)
        .where(cities.c.is_active.is_(True), latest_reading.c.reading_rank == 1)
        .order_by(cities.c.city_name)
    )
    with engine.connect() as connection:
        return connection.execute(statement).mappings().all()


def _city_exists(engine: Engine, city_id: str) -> bool:
    statement = select(cities.c.city_id).where(
        cities.c.city_id == city_id, cities.c.is_active.is_(True)
    )
    with engine.connect() as connection:
        return connection.scalar(statement) is not None


def create_app(
    engine: Engine | None = None,
    now_provider: Callable[[], datetime] | None = None,
) -> Flask:
    """Create the dashboard API; injectable dependencies keep endpoint tests isolated."""
    app = Flask(__name__)
    CORS(app)
    resolved_engine = engine or _get_engine()
    current_time = now_provider or (lambda: datetime.now(timezone.utc))

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(_error: SQLAlchemyError):
        return jsonify({"error": "database query failed"}), 500

    @app.get("/api/cities")
    def get_cities():
        return jsonify([
            {"id": row["city_id"], "cityName": _city_label(row["city_name"], row["state"], row["country"])}
            for row in _city_rows(resolved_engine)
        ])

    @app.get("/api/cities/overview")
    def get_cities_overview():
        return jsonify([
            {
                "id": row["city_id"],
                "cityName": _city_label(row["city_name"], row["state"], row["country"]),
                "aqi": row["aqi"],
                "observedAt": _as_utc(row["observed_at"]).isoformat(),
            }
            for row in _city_rows(resolved_engine)
        ])

    @app.get("/api/cities/<city_id>/trend")
    def get_city_trend(city_id: str):
        if not _city_exists(resolved_engine, city_id):
            return jsonify({"error": "city not found"}), 404

        end = _as_utc(current_time())
        start = end - timedelta(hours=24)
        city_statement = select(cities.c.city_name, cities.c.state, cities.c.country).where(cities.c.city_id == city_id)
        trend_statement = (
            select(gold_air_quality.c.observed_at, gold_air_quality.c.aqi)
            .where(
                gold_air_quality.c.city_id == city_id,
                gold_air_quality.c.observed_at >= start,
                gold_air_quality.c.observed_at <= end,
            )
            .order_by(gold_air_quality.c.observed_at)
        )
        with resolved_engine.connect() as connection:
            city = connection.execute(city_statement).mappings().one()
            trend = connection.execute(trend_statement).mappings().all()

        return jsonify({
            "id": city_id,
            "cityName": _city_label(city["city_name"], city["state"], city["country"]),
            "aqi": trend[-1]["aqi"] if trend else None,
            "trend": [
                {"observedAt": _as_utc(row["observed_at"]).isoformat(), "aqi": row["aqi"]}
                for row in trend
            ],
        })

    @app.get("/api/cities/<city_id>/aggregates")
    def get_city_aggregates(city_id: str):
        period = request.args.get("period", "daily")
        if period not in {"daily", "weekly"}:
            return jsonify({"error": "period must be daily or weekly"}), 400
        if not _city_exists(resolved_engine, city_id):
            return jsonify({"error": "city not found"}), 404

        end = _as_utc(current_time())
        start = end - timedelta(days=14)
        statement = (
            select(gold_air_quality.c.observed_at, gold_air_quality.c.aqi)
            .where(
                gold_air_quality.c.city_id == city_id,
                gold_air_quality.c.observed_at >= start,
                gold_air_quality.c.observed_at <= end,
            )
            .order_by(gold_air_quality.c.observed_at)
        )
        with resolved_engine.connect() as connection:
            readings = connection.execute(statement).mappings().all()

        daily_values: dict[str, list[int]] = defaultdict(list)
        for row in readings:
            daily_values[_as_utc(row["observed_at"]).date().isoformat()].append(row["aqi"])
        daily = [
            {"date": date, "aqi": round(sum(values) / len(values), 1)}
            for date, values in sorted(daily_values.items())
        ]
        if period == "daily":
            return jsonify(daily)

        weekly = []
        for index in range(0, len(daily), 7):
            week = daily[index : index + 7]
            weekly.append({
                "date": f"Week of {week[0]['date']}",
                "aqi": round(sum(day["aqi"] for day in week) / len(week), 1),
            })
        return jsonify(weekly)

    return app


if __name__ == "__main__":
    create_app().run(port=8000, debug=True)
