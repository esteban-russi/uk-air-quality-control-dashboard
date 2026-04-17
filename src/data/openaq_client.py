"""Async client for the OpenAQ v3 API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from src.config import (
    MEASUREMENT_WINDOW_HOURS,
    OPENAQ_API_KEY,
    OPENAQ_BASE_URL,
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


async def _fetch_sensor_hours(
    client: httpx.AsyncClient,
    sensor_id: int,
    date_from: datetime,
    date_to: datetime,
) -> list[dict]:
    """Fetch hourly measurements for a single sensor."""
    params = {
        "datetime_from": date_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "datetime_to": date_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": OPENAQ_MEASUREMENTS_LIMIT,
    }
    resp = await client.get(
        f"{OPENAQ_BASE_URL}/sensors/{sensor_id}/hours",
        params=params,
    )
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


async def fetch_city_data(city_name: str) -> CityAirQuality:
    """Fetch the last 48 hours of air quality data for a UK city.

    Args:
        city_name: One of the supported UK city names (e.g. "London").

    Returns:
        CityAirQuality with validated station and measurement data.
    """
    city = get_city(city_name)
    now = datetime.now(timezone.utc)
    date_from = now - timedelta(hours=MEASUREMENT_WINDOW_HOURS)

    stations: list[StationData] = []

    async with httpx.AsyncClient(headers=_headers(), timeout=30.0) as client:
        locations = await _fetch_locations(client, city)

        for loc in locations:
            loc_id: int = loc["id"]
            loc_name: str = loc.get("name", "")
            coords = loc.get("coordinates", {})
            lat = coords.get("latitude", 0.0)
            lon = coords.get("longitude", 0.0)

            sensors = _extract_sensors(loc)
            if not sensors:
                continue

            measurements: list[Measurement] = []
            for sensor in sensors:
                try:
                    raw_hours = await _fetch_sensor_hours(
                        client, sensor["id"], date_from, now
                    )
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Failed to fetch sensor %s: %s", sensor["id"], exc
                    )
                    continue

                for raw in raw_hours:
                    m = _parse_measurement(raw, sensor, loc_id, loc_name)
                    if m is not None:
                        measurements.append(m)

            if measurements:
                stations.append(
                    StationData(
                        location_id=loc_id,
                        name=loc_name,
                        latitude=lat,
                        longitude=lon,
                        measurements=measurements,
                    )
                )

    return CityAirQuality(city=city_name, stations=stations)
