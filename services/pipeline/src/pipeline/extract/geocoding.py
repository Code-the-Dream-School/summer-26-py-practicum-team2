from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import requests
from sqlalchemy.orm import Session

from pipeline.db.models import GeocodingCache


GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/direct"


class GeocodingError(Exception):
    """Base error for OpenWeather geocoding failures."""


class GeocodingConfigError(GeocodingError):
    """Raised when the geocoding client is missing required configuration."""


class GeocodingNotFoundError(GeocodingError):
    """Raised when OpenWeather returns no location matches."""


@dataclass(frozen=True)
class GeocodingResult:
    name: str
    lat: float
    lon: float
    country_code: str
    state: str | None = None
    cache_id: int | None = None


def build_geocoding_query(city: str, country_code: str, state: str | None = None) -> str:
    cleaned_city = city.strip()
    cleaned_country = country_code.strip().upper()
    cleaned_state = state.strip() if state else None

    if not cleaned_city:
        raise ValueError("city is required")
    if not cleaned_country:
        raise ValueError("country_code is required")

    parts = [cleaned_city]
    if cleaned_state:
        parts.append(cleaned_state)
    parts.append(cleaned_country)
    return ",".join(parts)


def get_geocoding_from_cache(db_session: Session, query: str) -> GeocodingResult | None:
    """Retrieve a cached geocoding result if it exists.

    Args:
        db_session: SQLAlchemy database session
        query: The geocoding query string

    Returns:
        GeocodingResult if found in cache, None otherwise
    """
    cached = db_session.query(GeocodingCache).filter_by(query_text=query).first()
    if cached:
        return GeocodingResult(
            name=cached.resolved_name,
            lat=float(cached.lat),
            lon=float(cached.lon),
            country_code=cached.resolved_country,
            state=cached.resolved_state,
            cache_id=cached.cache_id,
        )
    return None


def store_geocoding_in_cache(
    db_session: Session, query: str, result: GeocodingResult, raw_response: list | dict
) -> GeocodingResult:
    """Store a geocoding result (and the raw API payload) in the cache.

    Args:
        db_session: SQLAlchemy database session
        query: The geocoding query string
        result: The GeocodingResult to cache
        raw_response: The full, unmodified OpenWeather geocoding API response

    Returns:
        The same result, with cache_id populated from the newly inserted row.
    """
    cache_entry = GeocodingCache(
        query_text=query,
        lat=result.lat,
        lon=result.lon,
        resolved_name=result.name,
        resolved_country=result.country_code,
        resolved_state=result.state,
        raw_response=raw_response,
    )
    db_session.add(cache_entry)
    db_session.commit()
    db_session.refresh(cache_entry)
    return GeocodingResult(
        name=result.name,
        lat=result.lat,
        lon=result.lon,
        country_code=result.country_code,
        state=result.state,
        cache_id=cache_entry.cache_id,
    )


def geocode_city(
    raw_dir: Path | None,
    city: str,
    country_code: str,
    state: str | None = None,
    *,
    api_key: str | None = None,
    session: requests.Session | None = None,
    db_session: Session | None = None,
    limit: int = 1,
    timeout_seconds: float = 10.0,
) -> GeocodingResult:
    """Resolve a city into coordinates using the OpenWeather direct geocoding API.

    If db_session is provided, the geocoding result will be cached in the database
    to avoid redundant API calls for the same city.

    Args:
        raw_dir: Directory for raw response persistence (currently unused)
        city: City name
        country_code: ISO 2-letter country code
        state: Optional state/province name
        api_key: OpenWeather API key (defaults to OPENWEATHER_API_KEY env var)
        session: HTTP session for requests (defaults to new Session)
        db_session: SQLAlchemy session for caching (optional)
        limit: Number of results to request from API
        timeout_seconds: Request timeout in seconds

    Returns:
        GeocodingResult with lat/lon coordinates
    """
    del raw_dir  # Raw response persistence is handled by later tickets.

    query = build_geocoding_query(city=city, country_code=country_code, state=state)

    # Check cache first if db_session is provided
    if db_session:
        cached_result = get_geocoding_from_cache(db_session, query)
        if cached_result:
            return cached_result

    resolved_api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
    if not resolved_api_key:
        raise GeocodingConfigError("OPENWEATHER_API_KEY is required for geocoding requests")

    resolved_session = session or requests.Session()
    params = {"q": query, "limit": limit, "appid": resolved_api_key}

    try:
        response = resolved_session.get(GEOCODING_URL, params=params, timeout=timeout_seconds)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise GeocodingError(f"OpenWeather geocoding request failed for {query}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise GeocodingError("OpenWeather geocoding response was not valid JSON") from exc

    if not isinstance(payload, list) or not payload:
        raise GeocodingNotFoundError(f"No geocoding results found for {query}")

    first_match = payload[0]

    try:
        result = GeocodingResult(
            name=str(first_match["name"]),
            lat=float(first_match["lat"]),
            lon=float(first_match["lon"]),
            country_code=str(first_match["country"]).upper(),
            state=str(first_match["state"]) if first_match.get("state") else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodingError("OpenWeather geocoding response was missing expected fields") from exc

    # Store result in cache if db_session is provided
    if db_session:
        result = store_geocoding_in_cache(db_session, query, result, payload)

    return result
