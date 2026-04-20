"""Sidebar component — city selector and controls."""

from __future__ import annotations

import streamlit as st

from src.config import CITIES
from src.models.schemas import Pollutant
from src.ui.charts import POLLUTANT_META

_ALL_POLLUTANT_LABELS: list[str] = [meta["label"] for meta in POLLUTANT_META.values()]
_LABEL_TO_POLLUTANT: dict[str, Pollutant] = {
    meta["label"]: p for p, meta in POLLUTANT_META.items()
}


def render_sidebar() -> tuple[str, bool, Pollutant]:
    """Render the sidebar and return (selected_city, refresh_clicked, selected_pollutant)."""
    with st.sidebar:
        st.header("Controls")

        selected_city = st.selectbox(
            "Select a city",
            options=CITIES,
            index=CITIES.index(st.session_state.get("selected_city", CITIES[0])),
        )

        refresh = st.button("🔄 Refresh data")

        st.divider()
        st.subheader("Pollutant")
        selected_label = st.selectbox(
            "Select pollutant to display",
            options=_ALL_POLLUTANT_LABELS,
            index=0,
        )
        selected_pollutant = _LABEL_TO_POLLUTANT[selected_label]

        st.divider()
        st.markdown(
            "Data from [OpenAQ](https://openaq.org/) — last 48 hours."
        )

    return selected_city, refresh, selected_pollutant
