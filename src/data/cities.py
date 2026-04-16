"""UK city name → geographic coordinates for OpenAQ geospatial queries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CityCoordinates:
    name: str
    latitude: float
    longitude: float


# Coordinates are approximate city-centre points (WGS 84).
CITY_COORDINATES: dict[str, CityCoordinates] = {
    "London": CityCoordinates("London", 51.5074, -0.1278),
    "Manchester": CityCoordinates("Manchester", 53.4808, -2.2426),
    "Bristol": CityCoordinates("Bristol", 51.4545, -2.5879),
    "Birmingham": CityCoordinates("Birmingham", 52.4862, -1.8904),
    "Edinburgh": CityCoordinates("Edinburgh", 55.9533, -3.1883),
    "Leeds": CityCoordinates("Leeds", 53.8008, -1.5491),
    "Glasgow": CityCoordinates("Glasgow", 55.8642, -4.2518),
    "Cardiff": CityCoordinates("Cardiff", 51.4816, -3.1791),
    "Belfast": CityCoordinates("Belfast", 54.5973, -5.9301),
    "Liverpool": CityCoordinates("Liverpool", 53.4084, -2.9916),
}


def get_city(name: str) -> CityCoordinates:
    """Return coordinates for a city, raising KeyError if not found."""
    return CITY_COORDINATES[name]
