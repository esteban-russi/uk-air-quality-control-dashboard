from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- API keys ---
GOOGLE_AI_STUDIO_API_KEY: str = os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OPENAQ_API_KEY: str = os.getenv("OPENAQ_API_KEY", "")

# --- OpenAQ ---
OPENAQ_BASE_URL: str = "https://api.openaq.org/v3"
OPENAQ_SEARCH_RADIUS_M: int = 25_000  # metres, max allowed by API
OPENAQ_MEASUREMENTS_LIMIT: int = 1000
OPENAQ_MAX_CONCURRENT: int = 5  # cap on simultaneous sensor calls — protects rate limit
MEASUREMENT_WINDOW_HOURS: int = 48

# --- Time range options for the UI selector ---
# granularity drives which OpenAQ endpoint we hit: /sensors/{id}/hours vs /days
TIME_RANGES: dict[str, dict] = {
    "Last 24 hours": {"hours": 24, "granularity": "hours"},
    "Last 48 hours": {"hours": 48, "granularity": "hours"},
    "Last 7 days": {"hours": 168, "granularity": "days"},
    "Last 30 days": {"hours": 720, "granularity": "days"},
}
DEFAULT_RANGE_KEY: str = "Last 48 hours"

# --- Pollutants tracked ---
POLLUTANT_PARAMS: list[str] = ["pm25", "pm10", "no2", "o3", "so2", "co"]

# --- City list ---
CITIES: list[str] = [
    "London",
    "Manchester",
    "Bristol",
    "Birmingham",
    "Edinburgh",
    "Leeds",
    "Glasgow",
    "Cardiff",
    "Belfast",
    "Liverpool",
]

# --- Paths ---
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
