"""Tests for Pydantic schemas — validation edge cases."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models.schemas import (
    ChatMessage,
    CityAirQuality,
    Measurement,
    Pollutant,
    StationData,
)


# --- Measurement ---


class TestMeasurement:
    def test_valid_measurement(self):
        m = Measurement(
            value=12.5,
            parameter=Pollutant.PM25,
            unit="µg/m³",
            datetime_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime_to=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            location_id=100,
            sensor_id=200,
        )
        assert m.value == 12.5
        assert m.parameter == Pollutant.PM25

    def test_measurement_negative_value(self):
        """Negative values are allowed (some sensors report them)."""
        m = Measurement(
            value=-0.5,
            parameter=Pollutant.O3,
            unit="ppm",
            datetime_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime_to=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            location_id=1,
            sensor_id=2,
        )
        assert m.value == -0.5

    def test_measurement_invalid_pollutant(self):
        with pytest.raises(ValidationError):
            Measurement(
                value=10.0,
                parameter="invalid_param",
                unit="µg/m³",
                datetime_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime_to=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
                location_id=1,
                sensor_id=2,
            )

    def test_measurement_missing_required_field(self):
        with pytest.raises(ValidationError):
            Measurement(
                value=10.0,
                parameter=Pollutant.PM25,
                # missing unit, datetimes, ids
            )

    def test_measurement_from_string_pollutant(self):
        """Pollutant can be provided as a string matching enum value."""
        m = Measurement(
            value=5.0,
            parameter="no2",
            unit="µg/m³",
            datetime_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime_to=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            location_id=1,
            sensor_id=2,
        )
        assert m.parameter == Pollutant.NO2


# --- StationData ---


class TestStationData:
    def test_station_with_empty_measurements(self):
        s = StationData(
            location_id=42,
            name="Test Station",
            latitude=51.5,
            longitude=-0.1,
        )
        assert s.measurements == []

    def test_station_with_measurements(self):
        m = Measurement(
            value=10.0,
            parameter=Pollutant.PM10,
            unit="µg/m³",
            datetime_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime_to=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            location_id=42,
            sensor_id=100,
        )
        s = StationData(
            location_id=42,
            name="Test Station",
            latitude=51.5,
            longitude=-0.1,
            measurements=[m],
        )
        assert len(s.measurements) == 1


# --- CityAirQuality ---


class TestCityAirQuality:
    def test_empty_city(self):
        c = CityAirQuality(city="London")
        assert c.stations == []
        assert c.all_measurements == []

    def test_all_measurements_aggregates(self):
        m1 = Measurement(
            value=1.0,
            parameter=Pollutant.PM25,
            unit="µg/m³",
            datetime_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime_to=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            location_id=1,
            sensor_id=10,
        )
        m2 = Measurement(
            value=2.0,
            parameter=Pollutant.NO2,
            unit="µg/m³",
            datetime_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime_to=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            location_id=2,
            sensor_id=20,
        )
        c = CityAirQuality(
            city="London",
            stations=[
                StationData(location_id=1, name="S1", latitude=51.5, longitude=-0.1, measurements=[m1]),
                StationData(location_id=2, name="S2", latitude=51.6, longitude=-0.2, measurements=[m2]),
            ],
        )
        assert len(c.all_measurements) == 2

    def test_fetched_at_auto_set(self):
        c = CityAirQuality(city="London")
        assert c.fetched_at is not None


# --- ChatMessage ---


class TestChatMessage:
    def test_valid_user_message(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"

    def test_valid_assistant_message(self):
        msg = ChatMessage(role="assistant", content="Hi there")
        assert msg.role == "assistant"

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            ChatMessage(role="system", content="No")

    def test_empty_content_allowed(self):
        msg = ChatMessage(role="user", content="")
        assert msg.content == ""
