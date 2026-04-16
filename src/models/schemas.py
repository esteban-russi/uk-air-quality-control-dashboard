from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Pollutant(str, Enum):
    PM25 = "pm25"
    PM10 = "pm10"
    NO2 = "no2"
    O3 = "o3"
    SO2 = "so2"
    CO = "co"


class Measurement(BaseModel):
    """A single hourly measurement from a sensor."""

    value: float
    parameter: Pollutant
    unit: str
    datetime_from: datetime
    datetime_to: datetime
    location_id: int
    sensor_id: int
    location_name: str = ""


class StationData(BaseModel):
    """All measurements from one monitoring station."""

    location_id: int
    name: str
    latitude: float
    longitude: float
    measurements: list[Measurement] = Field(default_factory=list)


class CityAirQuality(BaseModel):
    """Aggregated air quality data for a city across its stations."""

    city: str
    stations: list[StationData] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def all_measurements(self) -> list[Measurement]:
        return [m for s in self.stations for m in s.measurements]


class ChatMessage(BaseModel):
    """A single chat message in the conversation."""

    role: str = Field(pattern=r"^(user|assistant)$")
    content: str
