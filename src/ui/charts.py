"""Plotly chart builders for air quality data."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.models.schemas import CityAirQuality, Pollutant

# Display names and colours per pollutant
POLLUTANT_META: dict[Pollutant, dict] = {
    Pollutant.PM25: {"label": "PM2.5", "color": "#e74c3c", "unit": "µg/m³"},
    Pollutant.PM10: {"label": "PM10", "color": "#e67e22", "unit": "µg/m³"},
    Pollutant.NO2:  {"label": "NO₂",  "color": "#8e44ad", "unit": "µg/m³"},
    Pollutant.O3:   {"label": "O₃",   "color": "#2980b9", "unit": "µg/m³"},
    Pollutant.SO2:  {"label": "SO₂",  "color": "#27ae60", "unit": "µg/m³"},
    Pollutant.CO:   {"label": "CO",   "color": "#95a5a6", "unit": "ppm"},
}

# WHO 24-hour guideline values (µg/m³ unless noted)
WHO_GUIDELINES: dict[Pollutant, float] = {
    Pollutant.PM25: 15.0,
    Pollutant.PM10: 45.0,
    Pollutant.NO2:  25.0,
    Pollutant.O3:   100.0,
    Pollutant.SO2:  40.0,
}


def _build_pollutant_chart(
    data: CityAirQuality,
    pollutant: Pollutant,
) -> go.Figure | None:
    """Build a time-series chart for a single pollutant across all stations."""
    meta = POLLUTANT_META[pollutant]

    # Collect measurements for this pollutant from all stations
    traces_added = False
    fig = go.Figure()

    for station in data.stations:
        measurements = [m for m in station.measurements if m.parameter == pollutant]
        if not measurements:
            continue

        measurements.sort(key=lambda m: m.datetime_from)
        times = [m.datetime_from for m in measurements]
        values = [m.value for m in measurements]

        fig.add_trace(go.Scatter(
            x=times,
            y=values,
            mode="lines+markers",
            name=station.name,
            marker=dict(size=4),
            line=dict(width=2),
        ))
        traces_added = True

    if not traces_added:
        return None

    # Add WHO guideline threshold line if available
    guideline = WHO_GUIDELINES.get(pollutant)
    if guideline is not None:
        fig.add_hline(
            y=guideline,
            line_dash="dash",
            line_color="red",
            opacity=0.6,
            annotation_text=f"WHO guideline ({guideline} {meta['unit']})",
            annotation_position="top left",
            annotation_font_size=10,
            annotation_font_color="red",
        )

    fig.update_layout(
        title=f"{meta['label']} ({meta['unit']})",
        xaxis_title="Time (UTC)",
        yaxis_title=meta["unit"],
        height=350,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    return fig


def render_charts(data: CityAirQuality) -> None:
    """Render Plotly charts for all available pollutants in a 2-column grid."""
    cols = st.columns(2)
    chart_idx = 0

    for pollutant in Pollutant:
        fig = _build_pollutant_chart(data, pollutant)
        if fig is None:
            continue
        with cols[chart_idx % 2]:
            st.plotly_chart(fig, use_container_width=True)
        chart_idx += 1

    if chart_idx == 0:
        st.warning("No measurement data available for any pollutant.")
