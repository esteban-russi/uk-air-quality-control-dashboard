"""Streamlit entry point for the UK Air Quality Dashboard."""

from __future__ import annotations

import asyncio

import streamlit as st

from src.config import CITIES
from src.data.openaq_client import fetch_city_data
from src.models.schemas import CityAirQuality
from src.ui.charts import render_charts
from src.ui.sidebar import render_sidebar

# --- Page config ---
st.set_page_config(
    page_title="UK Air Quality Dashboard",
    page_icon="🌬️",
    layout="wide",
)

# --- Session state init ---
if "city_data" not in st.session_state:
    st.session_state.city_data: CityAirQuality | None = None
if "selected_city" not in st.session_state:
    st.session_state.selected_city: str = CITIES[0]
if "fetch_error" not in st.session_state:
    st.session_state.fetch_error: str | None = None


def _fetch_data(city: str) -> None:
    """Fetch air quality data for the selected city."""
    try:
        st.session_state.fetch_error = None
        data = asyncio.run(fetch_city_data(city))
        st.session_state.city_data = data
    except Exception as exc:
        st.session_state.fetch_error = str(exc)
        st.session_state.city_data = None


# --- Sidebar ---
selected_city, refresh = render_sidebar()

# --- Fetch on city change or refresh ---
city_changed = selected_city != st.session_state.selected_city
if city_changed or refresh or st.session_state.city_data is None:
    st.session_state.selected_city = selected_city
    with st.spinner(f"Fetching air quality data for {selected_city}..."):
        _fetch_data(selected_city)

# --- Main content ---
st.title("🌬️ UK Air Quality Dashboard")
st.caption(f"Showing last 48 hours of data for **{st.session_state.selected_city}**")

if st.session_state.fetch_error:
    st.error(f"Failed to fetch data: {st.session_state.fetch_error}")
elif st.session_state.city_data is not None:
    data = st.session_state.city_data
    if not data.stations:
        st.warning(
            f"No monitoring stations with data found near {data.city}. "
            "Try another city or check back later."
        )
    else:
        st.info(
            f"Found **{len(data.stations)}** station(s) with "
            f"**{len(data.all_measurements)}** measurements."
        )
        render_charts(data)
