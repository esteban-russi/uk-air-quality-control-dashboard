"""Async client for the OpenAQ v3 API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from src.config import (
    MEASUREMENT_WINDOW_HOURS,
    OPENAQ_API_KEY,
    OPENAQ_BASE_URL,
    OPENAQ_MAX_CONCURRENT,
    OPENAQ_MEASUREMENTS_LIMIT,
    OPENAQ_SEARCH_RADIUS_M,
    POLLUTANT_PARAMS,
)
from src.data.cities import CityCoordinates, get_city
from src.models.schemas import (
    CityAirQuality,
    Measurement,
    Pollutant,
    StationData,
)

_VALID_GRANULARITIES: frozenset[str] = frozenset({"hours", "days"})

logger = logging.getLogger(__name__)


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if OPENAQ_API_KEY:
        headers["X-API-Key"] = OPENAQ_API_KEY
    return headers


async def _fetch_locations(
    client: httpx.AsyncClient,
    city: CityCoordinates,
) -> list[dict]:
    """Find monitoring locations near a city's coordinates."""
    params = {
        "coordinates": f"{city.latitude},{city.longitude}",
        "radius": OPENAQ_SEARCH_RADIUS_M,
        "limit": 100,
    }
    resp = await client.get(f"{OPENAQ_BASE_URL}/locations", params=params)
    if resp.status_code == 429:
        raise RuntimeError(
            "OpenAQ rate limit exceeded. Please wait a minute and try again."
        )
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def _extract_sensors(location: dict) -> list[dict]:
    """Return sensors from a location that measure tracked pollutants."""
    sensors = []
    for sensor in location.get("sensors", []):
        param = sensor.get("parameter", {})
        if param.get("name") in POLLUTANT_PARAMS:
            sensors.append(sensor)
    return sensors


async def _fetch_sensor_series(
    client: httpx.AsyncClient,
    sensor_id: int,
    date_from: datetime,
    date_to: datetime,
    granularity: str,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Fetch aggregated measurements for a single sensor.

    granularity must be 'hours' or 'days' — picks /sensors/{id}/hours or /days.
    semaphore caps simultaneous in-flight requests to protect rate limits.
    """
    params = {
        "datetime_from": date_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "datetime_to": date_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": OPENAQ_MEASUREMENTS_LIMIT,
    }
    url = f"{OPENAQ_BASE_URL}/sensors/{sensor_id}/{granularity}"
    async with semaphore:
        resp = await client.get(url, params=params)
    if resp.status_code == 429:
        logger.warning("Rate limited fetching sensor %s, skipping", sensor_id)
        return []
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def _parse_measurement(
    raw: dict,
    sensor: dict,
    location_id: int,
    location_name: str,
) -> Measurement | None:
    """Parse a single hourly result into a Measurement model."""
    param = sensor.get("parameter", {})
    param_name = param.get("name")
    if param_name not in Pollutant.__members__.values():
        try:
            pollutant = Pollutant(param_name)
        except ValueError:
            return None
    else:
        pollutant = Pollutant(param_name)

    period = raw.get("period", {})
    dt_from = period.get("datetimeFrom", {}).get("utc")
    dt_to = period.get("datetimeTo", {}).get("utc")
    if not dt_from or not dt_to:
        return None

    return Measurement(
        value=raw["value"],
        parameter=pollutant,
        unit=param.get("units", ""),
        datetime_from=datetime.fromisoformat(dt_from.replace("Z", "+00:00")),
        datetime_to=datetime.fromisoformat(dt_to.replace("Z", "+00:00")),
        location_id=location_id,
        sensor_id=sensor["id"],
        location_name=location_name,
    )


async def fetch_city_data(
    city_name: str,
    hours: int = MEASUREMENT_WINDOW_HOURS,
    granularity: str = "hours",
) -> CityAirQuality:
    """Fetch air quality data for a UK city over the requested window.

    Args:
        city_name: One of the supported UK city names (e.g. "London").
        hours: How far back to look. Default 48 h.
        granularity: 'hours' or 'days' — chooses the OpenAQ aggregation endpoint.
            Use 'days' for windows >72 h to keep payloads manageable.

    Returns:
        CityAirQuality with validated station and measurement data.
    """
    if granularity not in _VALID_GRANULARITIES:
        raise ValueError(
            f"granularity must be one of {sorted(_VALID_GRANULARITIES)}, got {granularity!r}"
        )

    city = get_city(city_name)
    now = datetime.now(timezone.utc)
    date_from = now - timedelta(hours=hours)

    stations: list[StationData] = []
    semaphore = asyncio.Semaphore(OPENAQ_MAX_CONCURRENT)

    async with httpx.AsyncClient(headers=_headers(), timeout=30.0) as client:
        locations = await _fetch_locations(client, city)

        # Build a flat list of (loc, sensor) pairs so we can fan out across all sensors at once
        loc_sensor_pairs: list[tuple[dict, dict]] = []
        for loc in locations:
            for sensor in _extract_sensors(loc):
                loc_sensor_pairs.append((loc, sensor))

        if not loc_sensor_pairs:
            return CityAirQuality(city=city_name, stations=[])

        results = await asyncio.gather(
            *[
                _fetch_sensor_series(client, sensor["id"], date_from, now, granularity, semaphore)
                for _, sensor in loc_sensor_pairs
            ],
            return_exceptions=True,
        )

        # Group measurements by location
        by_loc: dict[int, list[Measurement]] = {}
        loc_meta: dict[int, dict] = {}
        for (loc, sensor), raw_or_exc in zip(loc_sensor_pairs, results):
            loc_id: int = loc["id"]
            if isinstance(raw_or_exc, Exception):
                logger.warning("Failed to fetch sensor %s: %s", sensor["id"], raw_or_exc)
                continue
            loc_meta.setdefault(loc_id, loc)
            for raw in raw_or_exc:
                m = _parse_measurement(raw, sensor, loc_id, loc.get("name", ""))
                if m is not None:
                    by_loc.setdefault(loc_id, []).append(m)

        for loc_id, measurements in by_loc.items():
            if not measurements:
                continue
            loc = loc_meta[loc_id]
            coords = loc.get("coordinates", {})
            stations.append(
                StationData(
                    location_id=loc_id,
                    name=loc.get("name", ""),
                    latitude=coords.get("latitude", 0.0),
                    longitude=coords.get("longitude", 0.0),
                    measurements=measurements,
                )
            )

    return CityAirQuality(city=city_name, stations=stations)
