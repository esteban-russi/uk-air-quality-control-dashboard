"""Plotly chart builders for air quality data."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.models.schemas import CityAirQuality, Measurement, Pollutant

# Map band thresholds expressed as multiples of the WHO guideline.
# Values <= GOOD_RATIO are green, <= MODERATE_RATIO amber, above is red.
_GOOD_RATIO = 0.5
_MODERATE_RATIO = 1.0

_BAND_COLORS: dict[str, str] = {
    "good": "#27ae60",
    "moderate": "#f39c12",
    "poor": "#c0392b",
    "unknown": "#7f8c8d",
}
_BAND_ORDER: tuple[str, ...] = ("good", "moderate", "poor", "unknown")
_BAND_LABELS: dict[str, str] = {
    "good": "≤ ½ WHO guideline",
    "moderate": "≤ WHO guideline",
    "poor": "> WHO guideline",
    "unknown": "no recent reading",
}

# Display names, colours and descriptions per pollutant
POLLUTANT_META: dict[Pollutant, dict] = {
    Pollutant.PM25: {
        "label": "PM2.5", "name": "Fine Particulate Matter",
        "color": "#e74c3c", "unit": "µg/m³",
        "description": (
            "Tiny airborne particles smaller than 2.5 µm, produced by combustion, "
            "vehicle exhaust, and industrial processes. High levels are harmful — they "
            "penetrate deep into the lungs and bloodstream, increasing risks of heart "
            "and respiratory disease."
        ),
    },
    Pollutant.PM10: {
        "label": "PM10", "name": "Coarse Particulate Matter",
        "color": "#e67e22", "unit": "µg/m³",
        "description": (
            "Inhalable particles up to 10 µm in diameter from dust, construction, "
            "and road traffic. High levels irritate the airways and can worsen asthma "
            "and other lung conditions."
        ),
    },
    Pollutant.NO2: {
        "label": "NO₂", "name": "Nitrogen Dioxide",
        "color": "#8e44ad", "unit": "µg/m³",
        "description": (
            "A reddish-brown gas mainly emitted by road vehicles and power plants. "
            "High levels inflame the airways, reduce lung function, and contribute "
            "to smog and acid rain."
        ),
    },
    Pollutant.O3: {
        "label": "O₃", "name": "Ozone",
        "color": "#2980b9", "unit": "µg/m³",
        "description": (
            "A reactive gas formed when sunlight hits vehicle and industrial emissions. "
            "While the ozone layer is protective, ground-level ozone is harmful — high "
            "levels trigger breathing problems and aggravate lung diseases."
        ),
    },
    Pollutant.SO2: {
        "label": "SO₂", "name": "Sulphur Dioxide",
        "color": "#27ae60", "unit": "µg/m³",
        "description": (
            "A sharp-smelling gas released by burning fossil fuels, especially coal and oil. "
            "High levels constrict airways, worsen asthma, and contribute to acid rain and "
            "particulate pollution."
        ),
    },
    Pollutant.CO: {
        "label": "CO", "name": "Carbon Monoxide",
        "color": "#95a5a6", "unit": "ppm",
        "description": (
            "A colourless, odourless gas produced by incomplete combustion in vehicles and "
            "heating systems. High levels reduce the blood's ability to carry oxygen, causing "
            "headaches, dizziness, and at extreme concentrations, can be fatal."
        ),
    },
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
    range_label: str = "Last 48 hours",
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
        title=f"{meta['label']} ({meta['unit']}) — {range_label}",
        xaxis_title="Time (UTC)",
        yaxis_title=meta["unit"],
        height=500,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    return fig


def _classify_band(value: float | None, guideline: float | None) -> str:
    if value is None:
        return "unknown"
    if guideline is None:
        return "moderate"  # neutral colour when no WHO threshold exists (e.g. CO)
    ratio = value / guideline
    if ratio <= _GOOD_RATIO:
        return "good"
    if ratio <= _MODERATE_RATIO:
        return "moderate"
    return "poor"


def _latest_for_pollutant(
    measurements: list[Measurement], pollutant: Pollutant
) -> Measurement | None:
    """Return the most recent measurement for the given pollutant, if any."""
    relevant = [m for m in measurements if m.parameter == pollutant]
    if not relevant:
        return None
    return max(relevant, key=lambda m: m.datetime_from)


def _scale_marker_size(count: int, min_count: int, max_count: int) -> float:
    """Linearly scale a measurement count to a marker size between 10 and 22."""
    if max_count == min_count:
        return 14.0
    return 10.0 + (count - min_count) / (max_count - min_count) * 12.0


def _build_station_map(data: CityAirQuality, pollutant: Pollutant) -> go.Figure | None:
    """Build a station map coloured by latest reading vs WHO guideline.

    One Plotly trace per band so the legend doubles as a key.
    """
    if not data.stations:
        return None

    meta = POLLUTANT_META[pollutant]
    guideline = WHO_GUIDELINES.get(pollutant)

    # Marker sizing baseline — based on total measurements per station, not just this pollutant.
    counts = [len(s.measurements) for s in data.stations]
    min_count, max_count = min(counts), max(counts)

    # Group stations by band to drive the legend.
    bands: dict[str, dict[str, list]] = {
        b: {"lats": [], "lons": [], "names": [], "hover": [], "sizes": []}
        for b in _BAND_ORDER
    }

    for station in data.stations:
        latest = _latest_for_pollutant(station.measurements, pollutant)
        latest_value = latest.value if latest is not None else None
        band = _classify_band(latest_value, guideline)

        if latest is not None:
            ratio_str = (
                f"{latest_value / guideline * 100:.0f}% of WHO" if guideline else "no WHO threshold"
            )
            ts = latest.datetime_from.strftime("%Y-%m-%d %H:%M UTC")
            hover = (
                f"<b>{station.name}</b><br>"
                f"{meta['label']}: {latest_value:.1f} {meta['unit']} ({ratio_str})<br>"
                f"latest: {ts}<br>"
                f"{len(station.measurements)} total measurements"
            )
        else:
            hover = (
                f"<b>{station.name}</b><br>"
                f"No {meta['label']} reading in window<br>"
                f"{len(station.measurements)} total measurements"
            )

        bands[band]["lats"].append(station.latitude)
        bands[band]["lons"].append(station.longitude)
        bands[band]["names"].append(station.name)
        bands[band]["hover"].append(hover)
        bands[band]["sizes"].append(
            _scale_marker_size(len(station.measurements), min_count, max_count)
        )

    fig = go.Figure()
    any_added = False
    for band in _BAND_ORDER:
        bucket = bands[band]
        if not bucket["lats"]:
            continue
        fig.add_trace(go.Scattermapbox(
            lat=bucket["lats"],
            lon=bucket["lons"],
            mode="markers",
            name=f"{_BAND_LABELS[band]} ({len(bucket['lats'])})",
            marker=dict(size=bucket["sizes"], color=_BAND_COLORS[band], opacity=0.85),
            hovertext=bucket["hover"],
            hoverinfo="text",
        ))
        any_added = True

    if not any_added:
        return None

    all_lats = [s.latitude for s in data.stations]
    all_lons = [s.longitude for s in data.stations]
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=sum(all_lats) / len(all_lats), lon=sum(all_lons) / len(all_lons)),
            zoom=10,
        ),
        height=480,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor="rgba(255,255,255,0.6)",
        ),
    )

    return fig


def render_charts(
    data: CityAirQuality,
    pollutant: Pollutant | None = None,
    range_label: str = "Last 48 hours",
) -> None:
    """Render KPIs, a line chart, and a coloured station map for one pollutant."""
    if pollutant is None:
        pollutant = Pollutant.PM25

    meta = POLLUTANT_META[pollutant]

    # --- KPIs ---
    all_values = [
        m.value
        for s in data.stations
        for m in s.measurements
        if m.parameter == pollutant
    ]
    if all_values:
        guideline = WHO_GUIDELINES.get(pollutant)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Mean", f"{sum(all_values) / len(all_values):.1f} {meta['unit']}")
        col2.metric("Max", f"{max(all_values):.1f} {meta['unit']}")
        col3.metric("Min", f"{min(all_values):.1f} {meta['unit']}")
        if guideline is not None:
            pct_above = sum(1 for v in all_values if v > guideline) / len(all_values) * 100
            col4.metric("Above WHO Guideline", f"{pct_above:.0f}%")
        else:
            col4.metric("Readings", f"{len(all_values)}")

    # --- Line chart ---
    st.subheader("Time Series")
    line_fig = _build_pollutant_chart(data, pollutant, range_label=range_label)
    if line_fig is not None:
        st.plotly_chart(
            line_fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": f"{data.city}_{pollutant.value}",
                },
            },
        )
    else:
        st.warning(f"No data available for {meta['label']}.")
        return

    # --- Station map ---
    st.subheader("Monitoring Stations")
    st.caption(
        f"Stations are coloured by the most recent {meta['label']} reading vs the WHO guideline. "
        "Marker size reflects how many measurements the station reported in the selected window."
    )
    map_fig = _build_station_map(data, pollutant)
    if map_fig is not None:
        st.plotly_chart(map_fig, use_container_width=True)
