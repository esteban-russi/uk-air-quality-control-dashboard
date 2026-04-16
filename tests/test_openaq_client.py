"""Tests for OpenAQ client — mock API responses."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.data.openaq_client import (
    _extract_sensors,
    _parse_measurement,
    fetch_city_data,
)
from src.models.schemas import Pollutant


# --- Helpers ---


def _make_location(
    loc_id: int = 1,
    name: str = "Test Station",
    lat: float = 51.5,
    lon: float = -0.1,
    sensors: list[dict] | None = None,
) -> dict:
    if sensors is None:
        sensors = [
            {
                "id": 100,
                "name": "pm25 µg/m³",
                "parameter": {"id": 2, "name": "pm25", "units": "µg/m³", "displayName": "PM2.5"},
            }
        ]
    return {
        "id": loc_id,
        "name": name,
        "coordinates": {"latitude": lat, "longitude": lon},
        "sensors": sensors,
    }


def _make_hourly_result(value: float = 12.5) -> dict:
    return {
        "value": value,
        "parameter": {"id": 2, "name": "pm25", "units": "µg/m³"},
        "period": {
            "label": "hour",
            "interval": "01:00:00",
            "datetimeFrom": {"utc": "2024-06-01T10:00:00Z", "local": "2024-06-01T11:00:00+01:00"},
            "datetimeTo": {"utc": "2024-06-01T11:00:00Z", "local": "2024-06-01T12:00:00+01:00"},
        },
        "coordinates": None,
        "summary": None,
        "coverage": {
            "expectedCount": 1,
            "observedCount": 1,
            "percentComplete": 100.0,
        },
    }


# --- _extract_sensors ---


class TestExtractSensors:
    def test_filters_tracked_pollutants(self):
        location = _make_location(sensors=[
            {"id": 1, "parameter": {"name": "pm25"}},
            {"id": 2, "parameter": {"name": "wind_speed"}},
            {"id": 3, "parameter": {"name": "no2"}},
        ])
        result = _extract_sensors(location)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 3

    def test_empty_sensors(self):
        location = _make_location(sensors=[])
        assert _extract_sensors(location) == []


# --- _parse_measurement ---


class TestParseMeasurement:
    def test_valid_parse(self):
        raw = _make_hourly_result(value=15.0)
        sensor = {"id": 100, "parameter": {"name": "pm25", "units": "µg/m³"}}
        m = _parse_measurement(raw, sensor, location_id=1, location_name="Station A")
        assert m is not None
        assert m.value == 15.0
        assert m.parameter == Pollutant.PM25
        assert m.sensor_id == 100

    def test_missing_datetime_returns_none(self):
        raw = {"value": 10.0, "period": {}}
        sensor = {"id": 1, "parameter": {"name": "pm25", "units": "µg/m³"}}
        assert _parse_measurement(raw, sensor, 1, "X") is None

    def test_unknown_parameter_returns_none(self):
        raw = _make_hourly_result()
        sensor = {"id": 1, "parameter": {"name": "wind_speed", "units": "m/s"}}
        assert _parse_measurement(raw, sensor, 1, "X") is None


# --- fetch_city_data (integration with mocks) ---


class TestFetchCityData:
    @pytest.mark.asyncio
    async def test_returns_city_air_quality(self):
        location = _make_location()
        hourly = [_make_hourly_result(12.5), _make_hourly_result(15.0)]

        dummy_request = httpx.Request("GET", "https://api.openaq.org/v3/test")
        mock_responses = [
            httpx.Response(200, json={"results": [location]}, request=dummy_request),
            httpx.Response(200, json={"results": hourly}, request=dummy_request),
        ]

        async def mock_get(url, **kwargs):
            return mock_responses.pop(0)

        with patch("src.data.openaq_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = mock_get
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await fetch_city_data("London")

        assert result.city == "London"
        assert len(result.stations) == 1
        assert len(result.stations[0].measurements) == 2

    @pytest.mark.asyncio
    async def test_no_locations_returns_empty(self):
        with patch("src.data.openaq_client.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()

            dummy_request = httpx.Request("GET", "https://api.openaq.org/v3/test")

            async def mock_get(url, **kwargs):
                return httpx.Response(200, json={"results": []}, request=dummy_request)

            instance.get = mock_get
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await fetch_city_data("London")

        assert result.city == "London"
        assert result.stations == []

    @pytest.mark.asyncio
    async def test_invalid_city_raises(self):
        with pytest.raises(KeyError):
            await fetch_city_data("NotACity")
