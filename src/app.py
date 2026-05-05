"""Streamlit entry point for the UK Air Quality Dashboard."""

from __future__ import annotations

import asyncio

import streamlit as st

from src.config import CITIES
from src.data.openaq_client import fetch_city_data
from src.graph.chain import analysis_chain
from src.models.schemas import CityAirQuality, Pollutant
from src.ui.charts import POLLUTANT_META, render_charts
from src.ui.chat import render_chat

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
if "analysis" not in st.session_state:
    st.session_state.analysis: str = ""


def _fetch_and_analyse(city: str) -> None:
    """Fetch air quality data and run LLM analysis for the selected city."""
    try:
        st.session_state.fetch_error = None
        st.session_state.analysis = ""
        st.session_state.chat_history = []
        result = asyncio.run(
            analysis_chain.ainvoke({"city": city})
        )
        st.session_state.city_data = result.get("measurements")
        st.session_state.analysis = result.get("analysis", "")
        if result.get("error"):
            st.session_state.fetch_error = result["error"]
    except Exception as exc:
        st.session_state.fetch_error = str(exc)
        st.session_state.city_data = None
        st.session_state.analysis = ""


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
    with st.spinner(f"Fetching data and generating analysis for {selected_city}..."):
        _fetch_and_analyse(selected_city)

# --- Main content ---
if st.session_state.fetch_error:
    error_msg = st.session_state.fetch_error
    if "rate limit" in error_msg.lower() or "429" in error_msg:
        st.warning("⏳ API rate limit reached. Please wait a moment and try again.")
    elif "401" in error_msg or "unauthorized" in error_msg.lower():
        st.error("🔑 API authentication failed. Check your `OPENAQ_API_KEY` in `.env`.")
    elif "timeout" in error_msg.lower():
        st.warning("⏱️ Request timed out. The API may be slow — try again shortly.")
    else:
        st.error(f"Failed to fetch data: {error_msg}")
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

        # --- LLM Analysis ---
        if st.session_state.analysis:
            st.divider()
            st.subheader("AI Analysis")
            st.markdown(st.session_state.analysis)

        # --- Chat interface ---
        render_chat(data, st.session_state.analysis)
