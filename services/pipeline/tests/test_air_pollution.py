from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from pipeline.extract.air_pollution import (  # noqa: E402
    AIR_POLLUTION_HISTORY_URL,
    AirPollutionConfigError,
    AirPollutionError,
    fetch_air_pollution_history,
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


SAMPLE_ENTRY = {
    "dt": 1606482000,
    "main": {"aqi": 2},
    "components": {
        "co": 270.367,
        "no": 5.867,
        "no2": 43.184,
        "o3": 4.783,
        "so2": 14.544,
        "pm2_5": 13.448,
        "pm10": 15.524,
        "nh3": 0.289,
    },
}


def test_fetch_air_pollution_history_parses_and_flattens_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    session = FakeSession(FakeResponse({"coord": [35.7796, -78.6382], "list": [SAMPLE_ENTRY]}))
    start = datetime(2026, 8, 6, 23, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)

    records = fetch_air_pollution_history(
        lat=35.7796, lon=-78.6382, start=start, end=end, session=session
    )

    assert len(records) == 1
    record = records[0]
    assert record.dt == "2020-11-27T13:00:00+00:00"
    assert record.aqi == 2
    assert record.aqi_category == "Fair"
    assert record.co == pytest.approx(270.367)
    assert record.pm2_5 == pytest.approx(13.448)
    assert session.calls == [
        {
            "url": AIR_POLLUTION_HISTORY_URL,
            "params": {
                "lat": 35.7796,
                "lon": -78.6382,
                "start": int(start.timestamp()),
                "end": int(end.timestamp()),
                "appid": "test-key",
            },
            "timeout": 10.0,
        }
    ]


def test_fetch_air_pollution_history_raises_when_api_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    start = datetime(2026, 8, 6, 23, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(AirPollutionConfigError):
        fetch_air_pollution_history(lat=0, lon=0, start=start, end=end)


def test_fetch_air_pollution_history_rejects_inverted_window() -> None:
    start = datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 6, 23, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError):
        fetch_air_pollution_history(lat=0, lon=0, start=start, end=end, api_key="test-key")


def test_fetch_air_pollution_history_wraps_http_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    session = FakeSession(
        FakeResponse([], status_error=requests.HTTPError("401 Client Error: Unauthorized for url"))
    )
    start = datetime(2026, 8, 6, 23, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(AirPollutionError):
        fetch_air_pollution_history(lat=0, lon=0, start=start, end=end, session=session)


def test_fetch_air_pollution_history_wraps_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    session = FakeSession(FakeResponse({"coord": [0, 0], "list": [{"dt": 1606482000}]}))
    start = datetime(2026, 8, 6, 23, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(AirPollutionError):
        fetch_air_pollution_history(lat=0, lon=0, start=start, end=end, session=session)
