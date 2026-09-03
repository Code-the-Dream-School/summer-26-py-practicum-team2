from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.extract.city_input import load_cities, load_city_rows  # noqa: E402


def _write_cities(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_load_cities_returns_only_valid_active_rows(tmp_path: Path) -> None:
    csv_path = _write_cities(
        tmp_path / "cities.csv",
        """city_id,city_name,state,country,is_active
US_RAL_01,Raleigh,NC,US,TRUE
US_NYC_99,New York,NY,US,FALSE
bad_row,,,US,TRUE
GB_LON_01, London , , gb , TRUE
""",
    )

    rows = load_cities(csv_path)

    assert rows == [
        {
            "city_id": "US_RAL_01",
            "city_name": "Raleigh",
            "state": "NC",
            "country": "US",
            "is_active": "TRUE",
        },
        {
            "city_id": "GB_LON_01",
            "city_name": "London",
            "state": "",
            "country": "GB",
            "is_active": "TRUE",
        },
    ]


def test_load_city_rows_includes_inactive_records(tmp_path: Path) -> None:
    csv_path = _write_cities(
        tmp_path / "cities.csv",
        """city_id,city_name,state,country,is_active
US_RAL_01,Raleigh,NC,US,TRUE
US_NYC_99,New York,NY,US,FALSE
""",
    )

    rows = load_city_rows(csv_path)

    assert [row["city_id"] for row in rows] == ["US_RAL_01", "US_NYC_99"]
    assert rows[1]["is_active"] == "FALSE"


def test_load_city_rows_requires_contract_columns(tmp_path: Path) -> None:
    csv_path = _write_cities(tmp_path / "cities.csv", "city_name,country\nRaleigh,US\n")

    with pytest.raises(ValueError, match="missing required columns"):
        load_city_rows(csv_path)
