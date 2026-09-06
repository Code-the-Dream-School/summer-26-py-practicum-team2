from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

import requests


AIR_POLLUTION_HISTORY_URL = "https://api.openweathermap.org/data/2.5/air_pollution/history"

AQI_CATEGORIES = {
    1: "Good",
    2: "Fair",
    3: "Moderate",
    4: "Poor",
    5: "Very Poor",
}


class AirPollutionError(Exception):
    """Base error for OpenWeather air pollution failures."""


class AirPollutionConfigError(AirPollutionError):
    """Raised when the air pollution client is missing required configuration."""


@dataclass(frozen=True)
class AirQualityRecord:
    dt: str
    aqi: int
    aqi_category: str
    co: float
    no: float
    no2: float
    o3: float
    so2: float
    pm2_5: float
    pm10: float
    nh3: float

# Fetchs hourly historical air quality for a coordinate over a UTC time range.
def fetch_air_pollution_history(
    lat: float,
    lon: float,
    start: datetime,
    end: datetime,
    *,
    api_key: str | None = None,
    session: requests.Session | None = None,
    timeout_seconds: float = 10.0,
) -> list[AirQualityRecord]:

    if start > end:
        raise ValueError("start must be before end")

    resolved_api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
    if not resolved_api_key:
        raise AirPollutionConfigError("OPENWEATHER_API_KEY is required for air pollution requests")

    resolved_session = session or requests.Session()
    params = {
        "lat": lat,
        "lon": lon,
        "start": int(start.timestamp()),
        "end": int(end.timestamp()),
        "appid": resolved_api_key,
    }

    try:
        response = resolved_session.get(AIR_POLLUTION_HISTORY_URL, params=params, timeout=timeout_seconds)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise AirPollutionError(f"OpenWeather air pollution request failed for ({lat}, {lon})") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise AirPollutionError("OpenWeather air pollution response was not valid JSON") from exc

    try:
        entries = payload["list"]
    except (KeyError, TypeError) as exc:
        raise AirPollutionError("OpenWeather air pollution response was missing 'list'") from exc

    try:
        return [_parse_record(entry) for entry in entries]
    except (KeyError, TypeError, ValueError) as exc:
        raise AirPollutionError("OpenWeather air pollution response was missing expected fields") from exc


def _parse_record(entry: dict) -> AirQualityRecord:
    aqi = int(entry["main"]["aqi"])
    components = entry["components"]
    return AirQualityRecord(
        dt=datetime.fromtimestamp(int(entry["dt"]), tz=timezone.utc).isoformat(),
        aqi=aqi,
        aqi_category=AQI_CATEGORIES.get(aqi, "Unknown"),
        co=float(components["co"]),
        no=float(components["no"]),
        no2=float(components["no2"]),
        o3=float(components["o3"]),
        so2=float(components["so2"]),
        pm2_5=float(components["pm2_5"]),
        pm10=float(components["pm10"]),
        nh3=float(components["nh3"]),
    )
