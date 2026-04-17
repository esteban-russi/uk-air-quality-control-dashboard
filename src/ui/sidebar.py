"""Sidebar component — city selector and controls."""

from __future__ import annotations

import streamlit as st

from src.config import CITIES


def render_sidebar() -> tuple[str, bool]:
    """Render the sidebar and return (selected_city, refresh_clicked)."""
    with st.sidebar:
        st.header("Controls")

        selected_city = st.selectbox(
            "Select a city",
            options=CITIES,
            index=CITIES.index(st.session_state.get("selected_city", CITIES[0])),
        )

        refresh = st.button("🔄 Refresh data")

        st.divider()
        st.markdown(
            "Data from [OpenAQ](https://openaq.org/) — last 48 hours.\n\n"
            "Pollutants: PM2.5, PM10, NO₂, O₃, SO₂, CO"
        )

    return selected_city, refresh
