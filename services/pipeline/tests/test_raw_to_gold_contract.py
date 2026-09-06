"""Regression tests for the raw payload and gold load contracts.

AIR-36. Uses AIR-31 ``flatten_raw_response`` / ``read_gold_ready_rows`` so the
data contract cannot drift independently of the production mapper.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import BigInteger, create_engine, func, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.gold import POLLUTANTS, upsert_gold  # noqa: E402
from pipeline.db.models import (  # noqa: E402
    Base,
    City,
    GoldAirQuality,
    PipelineRun,
    PipelineRunStatus,
    RawResponse,
)
from pipeline.db.raw_responses import RawResponseRecord, save_raw_response  # noqa: E402
from pipeline.transform.raw_response_reader import (  # noqa: E402
    POLLUTANT_FIELDS,
    flatten_raw_response,
    read_gold_ready_rows,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "openweather_history_payload.json"
CONTRACT_OBSERVED_AT = datetime(2020, 11, 27, 13, 0, tzinfo=timezone.utc)
GOLD_ROW_FIELDS = ("city_id", "observed_at", "aqi", *POLLUTANTS)


# SQLite maps BigInteger to BIGINT; AUTOINCREMENT needs INTEGER PRIMARY KEY.
# sqlite-only, same override as test_raw_response_reader.py.
@compiles(BigInteger, "sqlite")
def _compile_big_integer_sqlite(type_, compiler, **kw):
    return "INTEGER"


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _seed_city(engine, city_id: str = "US_RAL_01") -> None:
    with Session(engine) as session:
        session.merge(
            City(
                city_id=city_id,
                city_name="Raleigh",
                state="NC",
                country="US",
                is_active=True,
            )
        )
        session.commit()


def _seed_run(engine) -> int:
    with Session(engine) as session:
        run = PipelineRun(
            run_id="test-raw-to-gold",
            source="openweather",
            history_hours=24,
            window_start_utc=datetime(2026, 8, 1, tzinfo=timezone.utc),
            window_end_utc=datetime(2026, 8, 2, tzinfo=timezone.utc),
            status=PipelineRunStatus.RUNNING,
            started_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _raw_row(payload, city_id: str = "US_RAL_01") -> RawResponse:
    return RawResponse(
        city_id=city_id,
        pipeline_run_id=1,
        window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        http_status=200,
        raw_response=payload,
    )


def test_representative_payload_keeps_contract_shape() -> None:
    payload = _load_fixture()
    sample = payload["list"][0]

    assert POLLUTANT_FIELDS == POLLUTANTS
    assert payload["coord"] == [35.7796, -78.6382]
    assert sample["dt"] == 1606482000
    assert sample["main"]["aqi"] == 2
    assert set(sample["components"]) == set(POLLUTANTS)

    rows = flatten_raw_response(_raw_row(payload))

    assert len(rows) == 1
    assert set(rows[0]) == set(GOLD_ROW_FIELDS)
    assert rows[0]["city_id"] == "US_RAL_01"
    assert rows[0]["observed_at"] == CONTRACT_OBSERVED_AT
    assert rows[0]["aqi"] == 2
    assert rows[0]["pm2_5"] == 13.448
    assert rows[0]["nh3"] == 0.289


def test_empty_payloads_are_valid_zero_row_results() -> None:
    assert flatten_raw_response(_raw_row(None)) == []
    assert flatten_raw_response(_raw_row({})) == []
    assert flatten_raw_response(_raw_row({"coord": [35.7, -78.6], "list": []})) == []


def test_missing_optional_pollutants_become_null_and_incomplete_hours_are_skipped() -> None:
    payload = {
        "coord": [35.7796, -78.6382],
        "list": [
            {
                "dt": 1606482000,
                "main": {"aqi": 3},
                "components": {"pm2_5": 8.1},
            },
            {"dt": 1606485600},
            {"main": {"aqi": 4}, "components": {"co": 1.0}},
        ],
    }

    rows = flatten_raw_response(_raw_row(payload))

    assert len(rows) == 1
    assert rows[0]["aqi"] == 3
    assert rows[0]["pm2_5"] == 8.1
    assert rows[0]["nh3"] is None
    assert rows[0]["co"] is None


def test_unknown_extra_fields_do_not_change_gold_shape() -> None:
    payload = _load_fixture()
    payload["new_openweather_field"] = {"ignored": True}
    payload["list"][0]["extra"] = "keep-going"
    payload["list"][0]["components"]["extra_pollutant"] = 99

    rows = flatten_raw_response(_raw_row(payload))

    assert set(rows[0]) == set(GOLD_ROW_FIELDS)
    assert "extra_pollutant" not in rows[0]


def test_repeated_city_hour_does_not_double_count() -> None:
    engine = _engine()
    _seed_city(engine)
    noon = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    payload = {
        "list": [
            {"dt": int(noon.timestamp()), "main": {"aqi": 2}, "components": {"no2": 11.0}},
            {"dt": int(noon.timestamp()), "main": {"aqi": 4}, "components": {"no2": 15.2, "pm2_5": 20.5}},
        ]
    }

    result = upsert_gold(flatten_raw_response(_raw_row(payload)), engine=engine)

    assert result.stored == 2
    assert result.inserted == 1
    assert result.updated == 1

    with Session(engine) as session:
        stored = session.scalars(select(GoldAirQuality)).all()
        assert len(stored) == 1
        assert stored[0].aqi == 4
        assert stored[0].no2 == Decimal("15.2")
        assert stored[0].pm2_5 == Decimal("20.5")
        assert stored[0].updated_at >= stored[0].created_at


def test_load_integration_saves_raw_payload_then_upserts_gold() -> None:
    engine = _engine()
    _seed_city(engine)
    run_id = _seed_run(engine)
    payload = _load_fixture()
    fetched_at = datetime(2026, 8, 12, 21, 45, tzinfo=timezone.utc)

    saved = save_raw_response(
        RawResponseRecord(
            city_id="US_RAL_01",
            run_id=run_id,
            window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
            window_end=datetime(2026, 8, 2, tzinfo=timezone.utc),
            http_status=200,
            raw_response=payload,
            fetched_at=fetched_at,
        ),
        engine=engine,
    )
    gold_result = upsert_gold(
        read_gold_ready_rows(city_id="US_RAL_01", engine=engine),
        engine=engine,
    )

    assert gold_result.inserted == 1
    assert gold_result.updated == 0

    with Session(engine) as session:
        raw = session.get(RawResponse, saved.raw_id)
        gold = session.scalars(select(GoldAirQuality)).one()
        assert raw is not None
        assert raw.http_status == 200
        assert raw.raw_response["list"][0]["main"]["aqi"] == 2
        assert session.scalar(select(func.count()).select_from(GoldAirQuality)) == 1
        assert gold.city_id == "US_RAL_01"
        assert gold.aqi == 2
        assert gold.pm2_5 == Decimal("13.448")
        assert gold.nh3 == Decimal("0.289")
        observed = gold.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        assert observed == CONTRACT_OBSERVED_AT
