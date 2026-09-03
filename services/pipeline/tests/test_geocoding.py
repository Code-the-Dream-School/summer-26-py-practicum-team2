from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLSession


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.db.models import Base, GeocodingCache  # noqa: E402
from pipeline.extract.geocoding import (  # noqa: E402
    GEOCODING_URL,
    GeocodingConfigError,
    GeocodingError,
    GeocodingNotFoundError,
    GeocodingResult,
    build_geocoding_query,
    geocode_city,
    get_geocoding_from_cache,
    store_geocoding_in_cache,
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


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = SQLSession(engine)
    yield session
    session.close()
    engine.dispose()


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


def test_get_geocoding_from_cache_returns_none_when_not_cached(db_session) -> None:
    """Test that cache lookup returns None for uncached queries."""
    result = get_geocoding_from_cache(db_session, "Raleigh,NC,US")
    assert result is None


def test_get_geocoding_from_cache_returns_cached_result(db_session) -> None:
    """Test that cache stores and retrieves geocoding results."""
    cache_entry = GeocodingCache(
        geocoding_query="Raleigh,NC,US",
        latitude=35.7796,
        longitude=-78.6382,
        name="Raleigh",
        country_code="US",
        state="NC",
    )
    db_session.add(cache_entry)
    db_session.commit()

    result = get_geocoding_from_cache(db_session, "Raleigh,NC,US")
    assert result is not None
    assert result.lat == pytest.approx(35.7796)
    assert result.lon == pytest.approx(-78.6382)
    assert result.name == "Raleigh"
    assert result.country_code == "US"
    assert result.state == "NC"


def test_store_geocoding_in_cache(db_session) -> None:
    """Test that geocoding results are stored in cache."""
    result = GeocodingResult(
        name="Raleigh",
        lat=35.7796,
        lon=-78.6382,
        country_code="US",
        state="NC",
    )

    store_geocoding_in_cache(db_session, "Raleigh,NC,US", result)

    # Verify it was stored
    cached = get_geocoding_from_cache(db_session, "Raleigh,NC,US")
    assert cached is not None
    assert cached.lat == pytest.approx(35.7796)


def test_geocode_city_uses_cache_when_available(monkeypatch: pytest.MonkeyPatch, db_session) -> None:
    """Test that geocode_city returns cached result without making API call."""
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    
    # Pre-populate cache
    cache_entry = GeocodingCache(
        geocoding_query="Raleigh,NC,US",
        latitude=35.7796,
        longitude=-78.6382,
        name="Raleigh",
        country_code="US",
        state="NC",
    )
    db_session.add(cache_entry)
    db_session.commit()

    # This session should not make any API calls
    fake_session = FakeSession(FakeResponse([]))
    result = geocode_city(
        raw_dir=None,
        city="Raleigh",
        country_code="US",
        state="NC",
        session=fake_session,
        db_session=db_session,
    )

    # Should return cached result without calling API
    assert result.lat == pytest.approx(35.7796)
    assert result.lon == pytest.approx(-78.6382)
    assert len(fake_session.calls) == 0  # No API call was made


def test_geocode_city_stores_result_in_cache(monkeypatch: pytest.MonkeyPatch, db_session) -> None:
    """Test that geocode_city caches the result after API call."""
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    fake_session = FakeSession(
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
        session=fake_session,
        db_session=db_session,
    )

    # Verify it was cached
    cached = get_geocoding_from_cache(db_session, "Raleigh,NC,US")
    assert cached is not None
    assert cached.lat == pytest.approx(result.lat)
    assert cached.lon == pytest.approx(result.lon)


def test_geocode_city_wraps_http_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    session = FakeSession(
        FakeResponse([], status_error=requests.HTTPError("401 Client Error: Unauthorized for url"))
    )

    with pytest.raises(GeocodingError):
        geocode_city(raw_dir=None, city="Raleigh", country_code="US", session=session)
