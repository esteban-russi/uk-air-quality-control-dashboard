"""Streamlit entry point for the UK Air Quality Dashboard."""

from __future__ import annotations

import asyncio

import streamlit as st

from src.config import CITIES, DEFAULT_RANGE_KEY, TIME_RANGES
from src.graph.chain import analysis_chain
from src.models.schemas import Pollutant
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
# `cache` holds fetched data + analysis keyed by (city, range_key) so toggling
# between ranges or revisiting a city does not re-hit the OpenAQ API.
if "cache" not in st.session_state:
    st.session_state.cache = {}
if "selected_city" not in st.session_state:
    st.session_state.selected_city = CITIES[0]
if "selected_range_key" not in st.session_state:
    st.session_state.selected_range_key = DEFAULT_RANGE_KEY
if "fetch_error" not in st.session_state:
    st.session_state.fetch_error = None


def _fetch_and_analyse(city: str, range_key: str, force: bool = False) -> None:
    """Fetch air quality data and run LLM analysis, caching by (city, range_key)."""
    cache_key = (city, range_key)
    if not force and cache_key in st.session_state.cache:
        # Cache hit — clear stale chat from the previous selection.
        st.session_state.fetch_error = None
        st.session_state.chat_history = []
        return

    range_cfg = TIME_RANGES[range_key]
    try:
        st.session_state.fetch_error = None
        st.session_state.chat_history = []
        result = asyncio.run(
            analysis_chain.ainvoke({
                "city": city,
                "hours": range_cfg["hours"],
                "granularity": range_cfg["granularity"],
                "range_label": range_key.lower(),
            })
        )
        if result.get("error"):
            st.session_state.fetch_error = result["error"]
            return
        st.session_state.cache[cache_key] = {
            "data": result.get("measurements"),
            "analysis": result.get("analysis", ""),
        }
    except Exception as exc:
        st.session_state.fetch_error = str(exc)


def _current_entry() -> dict | None:
    """Return the cached entry for the current (city, range) selection, or None."""
    key = (st.session_state.selected_city, st.session_state.selected_range_key)
    return st.session_state.cache.get(key)


# --- Title ---
st.title("Real-time air quality monitoring for UK cities")

# --- Description ---
("Monitor air pollution levels across major UK cities using live data from "
 "the OpenAQ network. Select a city, explore pollutant concentrations over "
 "the last 48 hours, compare readings against WHO guidelines, and locate "
 "nearby monitoring stations on an interactive map.")


# --- City + range + refresh (top row) ---
st.caption(
    "Select a city and time range, then click 'Refresh data' to fetch the latest measurements. "
    "Cached results are reused when you switch back."
)
col_city, col_range, col_btn = st.columns([3, 2, 1])
with col_city:
    selected_city = st.selectbox(
        "City",
        options=CITIES,
        index=CITIES.index(st.session_state.selected_city),
        label_visibility="collapsed",
    )
with col_range:
    range_options = list(TIME_RANGES.keys())
    selected_range_key = st.selectbox(
        "Range",
        options=range_options,
        index=range_options.index(st.session_state.selected_range_key),
        label_visibility="collapsed",
    )
with col_btn:
    refresh = st.button("Refresh data", use_container_width=True)


# --- Resolve fetch: refresh forces a new call; selection change uses cache when present ---
selection_changed = (
    selected_city != st.session_state.selected_city
    or selected_range_key != st.session_state.selected_range_key
)
st.session_state.selected_city = selected_city
st.session_state.selected_range_key = selected_range_key

cache_key = (selected_city, selected_range_key)
need_fetch = refresh or cache_key not in st.session_state.cache

if need_fetch:
    spinner_msg = (
        f"Fetching {selected_range_key.lower()} for {selected_city} and generating analysis..."
        if cache_key not in st.session_state.cache
        else f"Refreshing {selected_city}..."
    )
    with st.spinner(spinner_msg):
        _fetch_and_analyse(selected_city, selected_range_key, force=refresh)
elif selection_changed:
    # Switching to an already-cached entry — reset transient chat state without refetch.
    st.session_state.fetch_error = None
    st.session_state.chat_history = []

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
else:
    entry = _current_entry()
    if entry is None or entry["data"] is None:
        st.info("Loading...")
    else:
        data = entry["data"]
        analysis = entry["analysis"]
        if not data.stations:
            st.warning(
                f"No monitoring stations with data found near {data.city} "
                f"for {selected_range_key.lower()}. Try another city or a different range."
            )
        else:
            fetched = data.fetched_at.strftime("%Y-%m-%d %H:%M UTC")
            st.info(
                f"Found **{len(data.stations)}** station(s) with "
                f"**{len(data.all_measurements)}** measurements over **{selected_range_key.lower()}**. "
                f"Last updated {fetched}."
            )
            st.divider()
            st.caption("Select a pollutant below to view charts and station map.")
            # --- Pollutant selector (below info) ---
            selected_label = st.selectbox(
                "Pollutant",
                options=_ALL_POLLUTANT_OPTIONS,
                index=0,
                label_visibility="collapsed",
            )
            selected_pollutant = _OPTION_TO_POLLUTANT[selected_label]
            st.markdown(POLLUTANT_META[selected_pollutant]["description"])

            render_charts(data, selected_pollutant, range_label=selected_range_key)

            # --- LLM Analysis ---
            if analysis:
                st.divider()
                st.subheader("AI Analysis")
                st.markdown(analysis)

            # --- Chat interface ---
            render_chat(data, analysis)
