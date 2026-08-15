from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.extract.geocoding import (  # noqa: E402
    GEOCODING_URL,
    GeocodingConfigError,
    GeocodingError,
    GeocodingNotFoundError,
    build_geocoding_query,
    geocode_city,
)


class FakeResponse:
    def __init__(self, payload, *, status_error: Exception | None = None):
        self._payload = payload
        self._status_error = status_error

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls: list[dict] = []

    def get(self, url: str, *, params: dict, timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.response


def test_build_geocoding_query_includes_state_when_present() -> None:
    assert build_geocoding_query("Raleigh", "us", "NC") == "Raleigh,NC,US"


def test_geocode_city_returns_first_matching_location(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    session = FakeSession(
        FakeResponse(
            [
                {
                    "name": "Raleigh",
                    "lat": 35.7796,
                    "lon": -78.6382,
                    "country": "US",
                    "state": "NC",
                }
            ]
        )
    )

    result = geocode_city(
        raw_dir=None,
        city="Raleigh",
        country_code="US",
        state="NC",
        session=session,
    )

    assert result.lat == pytest.approx(35.7796)
    assert result.lon == pytest.approx(-78.6382)
    assert result.country_code == "US"
    assert result.state == "NC"
    assert session.calls == [
        {
            "url": GEOCODING_URL,
            "params": {"q": "Raleigh,NC,US", "limit": 1, "appid": "test-key"},
            "timeout": 10.0,
        }
    ]


def test_geocode_city_raises_when_api_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)

    with pytest.raises(GeocodingConfigError):
        geocode_city(raw_dir=None, city="Raleigh", country_code="US")


def test_geocode_city_raises_when_no_matches_are_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    session = FakeSession(FakeResponse([]))

    with pytest.raises(GeocodingNotFoundError):
        geocode_city(raw_dir=None, city="Missing City", country_code="US", session=session)


def test_geocode_city_wraps_http_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    session = FakeSession(
        FakeResponse([], status_error=requests.HTTPError("401 Client Error: Unauthorized for url"))
    )

    with pytest.raises(GeocodingError):
        geocode_city(raw_dir=None, city="Raleigh", country_code="US", session=session)
