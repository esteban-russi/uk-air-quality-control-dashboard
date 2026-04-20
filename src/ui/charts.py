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
    fig = go.Figure()
    traces_added = False

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
        title=f"{meta['label']} ({meta['unit']}) — Last 48 h",
        xaxis_title="Time (UTC)",
        yaxis_title=meta["unit"],
        height=500,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    return fig


def _build_station_map(data: CityAirQuality) -> go.Figure | None:
    """Build a Mapbox scatter map of monitoring stations."""
    if not data.stations:
        return None

    lats = [s.latitude for s in data.stations]
    lons = [s.longitude for s in data.stations]
    names = [s.name for s in data.stations]
    counts = [len(s.measurements) for s in data.stations]
    hover = [f"{n}<br>{c} measurements" for n, c in zip(names, counts)]

    fig = go.Figure(go.Scattermapbox(
        lat=lats,
        lon=lons,
        mode="markers+text",
        marker=dict(size=12, color="#2980b9"),
        text=names,
        textposition="top center",
        hovertext=hover,
        hoverinfo="text",
    ))

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=sum(lats) / len(lats), lon=sum(lons) / len(lons)),
            zoom=10,
        ),
        height=450,
        margin=dict(l=0, r=0, t=0, b=0),
    )

    return fig


def render_charts(data: CityAirQuality, pollutant: Pollutant | None = None) -> None:
    """Render a line chart for one pollutant and a station map."""
    if pollutant is None:
        pollutant = Pollutant.PM25

    # --- Line chart ---
    line_fig = _build_pollutant_chart(data, pollutant)
    if line_fig is not None:
        st.plotly_chart(line_fig, use_container_width=True)
    else:
        st.warning(f"No data available for {POLLUTANT_META[pollutant]['label']}.")
        return

    # --- Station map ---
    st.subheader("Monitoring Stations")
    map_fig = _build_station_map(data)
    if map_fig is not None:
        st.plotly_chart(map_fig, use_container_width=True)
