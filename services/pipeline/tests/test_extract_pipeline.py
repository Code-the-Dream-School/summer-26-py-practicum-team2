from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.extract import pipeline as extract_pipeline  # noqa: E402
from pipeline.extract.geocoding import GeocodingNotFoundError, GeocodingResult  # noqa: E402


CITY = {"city_id": "US_RAL_01", "city_name": "Raleigh", "state": "", "country": "US"}


def test_extract_city_returns_geocode_and_history(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        extract_pipeline,
        "geocode_city",
        lambda **kwargs: GeocodingResult(
            name="Raleigh", lat=35.7796, lon=-78.6382, country_code="US", state="NC"
        ),
    )
    monkeypatch.setattr(
        extract_pipeline, "fetch_air_pollution_history", lambda **kwargs: ["record"]
    )

    result = extract_pipeline.extract_city(CITY)

    assert result == {
        "city_id": "US_RAL_01",
        "city_name": "Raleigh",
        "country": "US",
        "lat": 35.7796,
        "lon": -78.6382,
        "records": ["record"],
    }


def test_extract_city_returns_none_when_geocoding_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_not_found(**kwargs):
        raise GeocodingNotFoundError("no match")

    monkeypatch.setattr(extract_pipeline, "geocode_city", raise_not_found)

    assert extract_pipeline.extract_city(CITY) is None


def test_extract_cities_skips_failed_cities_and_keeps_the_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    good_city = {"city_id": "US_RAL_01", "city_name": "Raleigh", "state": "", "country": "US"}
    bad_city = {"city_id": "XX_NOPE_01", "city_name": "Nowhere", "state": "", "country": "XX"}

    def fake_geocode(*, city, **kwargs):
        if city == "Nowhere":
            raise GeocodingNotFoundError("no match")
        return GeocodingResult(name=city, lat=1.0, lon=2.0, country_code="US")

    monkeypatch.setattr(extract_pipeline, "geocode_city", fake_geocode)
    monkeypatch.setattr(
        extract_pipeline, "fetch_air_pollution_history", lambda **kwargs: ["record"]
    )

    results = extract_pipeline.extract_cities([good_city, bad_city])

    assert len(results) == 1
    assert results[0]["city_id"] == "US_RAL_01"
