"""Streamlit entry point for the UK Air Quality Dashboard."""

from __future__ import annotations

import asyncio

import streamlit as st

from src.config import CITIES
from src.data.openaq_client import fetch_city_data
from src.models.schemas import CityAirQuality, Pollutant
from src.ui.charts import POLLUTANT_META, render_charts

# --- Page config ---
st.set_page_config(
    page_title="UK Air Quality Dashboard",
    page_icon="🌬️",
    layout="wide",
)

# --- Pollutant lookup tables ---
_ALL_POLLUTANT_OPTIONS: list[str] = [
    f"{meta['name']} ({meta['label']})" for meta in POLLUTANT_META.values()
]
_OPTION_TO_POLLUTANT: dict[str, Pollutant] = {
    f"{meta['name']} ({meta['label']})": p for p, meta in POLLUTANT_META.items()
}

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


# --- Title ---
st.title("Real-time air quality monitoring for UK cities")

# --- Description ---
("Monitor air pollution levels across major UK cities using live data from "
 "the OpenAQ network. Select a city, explore pollutant concentrations over "
 "the last 48 hours, compare readings against WHO guidelines, and locate "
 "nearby monitoring stations on an interactive map.")


# --- City selector + refresh (top row) ---
st.caption(f"Select a city and click 'Refresh data' to fetch the latest air quality measurements ")
col_city, col_btn = st.columns([3, 1])
with col_city:
    selected_city = st.selectbox(
        "City",
        options=CITIES,
        index=CITIES.index(st.session_state.get("selected_city", CITIES[0])),
        label_visibility="collapsed",
    )
with col_btn:
    refresh = st.button("Refresh data", use_container_width=True)



# --- Fetch only on button press or first load ---
if refresh or st.session_state.city_data is None:
    st.session_state.selected_city = selected_city
    with st.spinner(f"Fetching air quality data for {selected_city}..."):
        _fetch_data(selected_city)

# --- Main content ---
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
        st.divider()
        st.caption(f"Select a pollutant below to view charts and station map.")
        # --- Pollutant selector (below info) ---
        selected_label = st.selectbox(
            "Pollutant",
            options=_ALL_POLLUTANT_OPTIONS,
            index=0,
            label_visibility="collapsed",
        )
        selected_pollutant = _OPTION_TO_POLLUTANT[selected_label]
        st.markdown(POLLUTANT_META[selected_pollutant]["description"])

        render_charts(data, selected_pollutant)
