from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.cities import import_cities, load_cities_from_db  # noqa: E402
from pipeline.db.models import Base, City  # noqa: E402
from pipeline.db.seed import get_cities_file  # noqa: E402


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _write_cities(path: Path) -> Path:
    path.write_text(
        """city_id,city_name,state,country,is_active
US_RAL_01, Raleigh ,NC,us,TRUE
US_NYC_99,New York,NY,US,FALSE
skipped,,,US,TRUE
GB_LON_01,London,,GB,TRUE
""",
        encoding="utf-8",
    )
    return path


def test_import_cities_upserts_valid_rows_including_inactive(tmp_path: Path) -> None:
    engine = _engine()
    csv_path = _write_cities(tmp_path / "cities.csv")

    result = import_cities(csv_path, engine=engine)

    assert result.stored == 3
    assert result.active == 2
    assert result.inactive == 1

    with Session(engine) as session:
        stored = {
            city.city_id: city for city in session.scalars(select(City)).all()
        }

    assert "skipped" not in stored
    assert stored["US_RAL_01"].city_name == "Raleigh"
    assert stored["US_RAL_01"].country == "US"
    assert stored["US_RAL_01"].is_active is True
    assert stored["GB_LON_01"].state is None
    assert stored["US_NYC_99"].is_active is False


def test_import_cities_updates_existing_rows(tmp_path: Path) -> None:
    engine = _engine()
    first_path = tmp_path / "first.csv"
    first_path.write_text(
        "city_id,city_name,state,country,is_active\nUS_RAL_01,Raleigh,NC,US,TRUE\n",
        encoding="utf-8",
    )
    second_path = tmp_path / "second.csv"
    second_path.write_text(
        "city_id,city_name,state,country,is_active\nUS_RAL_01,Raleigh,NC,US,FALSE\n",
        encoding="utf-8",
    )

    import_cities(first_path, engine=engine)
    import_cities(second_path, engine=engine)

    with Session(engine) as session:
        city = session.get(City, "US_RAL_01")

    assert city is not None
    assert city.is_active is False


def test_load_cities_from_db_matches_week2_loader_shape(tmp_path: Path) -> None:
    engine = _engine()
    import_cities(_write_cities(tmp_path / "cities.csv"), engine=engine)

    active_rows = load_cities_from_db(engine)
    all_rows = load_cities_from_db(engine, active_only=False)

    assert [row["city_id"] for row in active_rows] == ["GB_LON_01", "US_RAL_01"]
    assert active_rows[1] == {
        "city_id": "US_RAL_01",
        "city_name": "Raleigh",
        "state": "NC",
        "country": "US",
        "is_active": "TRUE",
    }
    assert [row["city_id"] for row in all_rows] == ["GB_LON_01", "US_NYC_99", "US_RAL_01"]
    assert all_rows[1]["is_active"] == "FALSE"


def test_get_cities_file_uses_env_then_default(monkeypatch, tmp_path: Path) -> None:
    configured = tmp_path / "custom-cities.csv"
    monkeypatch.setenv("CITIES_FILE", str(configured))
    assert get_cities_file() == configured

    monkeypatch.delenv("CITIES_FILE")
    assert get_cities_file().name == "cities.csv"
    assert get_cities_file().parent.name == "config"
