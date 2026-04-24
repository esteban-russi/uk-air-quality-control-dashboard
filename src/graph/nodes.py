"""LangGraph node functions: retrieve, analyze, respond."""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import GEMINI_MODEL, GOOGLE_AI_STUDIO_API_KEY
from src.data.openaq_client import fetch_city_data
from src.graph.state import GraphState
from src.models.schemas import ChatMessage, Measurement, Pollutant

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# WHO 24-hour guideline values (µg/m³ unless noted)
_WHO_GUIDELINES: dict[str, str] = {
    "pm25": "15 µg/m³",
    "pm10": "45 µg/m³",
    "no2": "25 µg/m³",
    "o3": "100 µg/m³",
    "so2": "40 µg/m³",
}

_ANALYSIS_SYSTEM_PROMPT = (_PROMPTS_DIR / "analysis.txt").read_text()
_RESPOND_SYSTEM_PROMPT = (_PROMPTS_DIR / "respond.txt").read_text()


def _format_who_guidelines() -> str:
    """Format WHO guidelines for inclusion in the system prompt."""
    return "\n      ".join(
        f"- {param.upper()}: {val}" for param, val in _WHO_GUIDELINES.items()
    )


def _summarise_measurements(measurements: list[Measurement]) -> str:
    """Build a compact text summary of measurements for the LLM context."""
    if not measurements:
        return "No measurements available."

    by_pollutant: dict[Pollutant, list[Measurement]] = {}
    for m in measurements:
        by_pollutant.setdefault(m.parameter, []).append(m)

    lines: list[str] = []
    for pollutant, ms in sorted(by_pollutant.items(), key=lambda x: x[0].value):
        ms.sort(key=lambda m: m.datetime_from)
        values = [m.value for m in ms]
        stations = sorted({m.location_name for m in ms})
        avg = sum(values) / len(values)
        lines.append(
            f"  {pollutant.value.upper()} ({ms[0].unit}): "
            f"{len(ms)} readings, "
            f"min={min(values):.1f}, max={max(values):.1f}, avg={avg:.1f}, "
            f"stations: {', '.join(stations)}"
        )
    return "\n".join(lines)


def _get_llm() -> ChatGoogleGenerativeAI:
    """Instantiate the Gemini LLM."""
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_AI_STUDIO_API_KEY,
        temperature=0.3,
    )


# ---------------------------------------------------------------------------
# Node: retrieve
# ---------------------------------------------------------------------------

async def retrieve(state: GraphState) -> GraphState:
    """Fetch air quality data from OpenAQ for the selected city."""
    city = state["city"]
    logger.info("Retrieving air quality data for %s", city)
    try:
        data = await fetch_city_data(city)
        return {**state, "measurements": data, "error": ""}
    except Exception as exc:
        logger.exception("Failed to retrieve data for %s", city)
        return {**state, "measurements": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Node: analyze
# ---------------------------------------------------------------------------

async def analyze(state: GraphState) -> GraphState:
    """Generate an LLM analysis summary of the air quality data."""
    data = state.get("measurements")
    if data is None or state.get("error"):
        return {**state, "analysis": ""}

    summary = _summarise_measurements(data.all_measurements)
    system_prompt = _ANALYSIS_SYSTEM_PROMPT.format(
        who_guidelines=_format_who_guidelines(),
    )
    user_content = (
        f"City: {data.city}\n"
        f"Stations reporting: {len(data.stations)}\n"
        f"Total measurements: {len(data.all_measurements)}\n"
        f"Measurement window: last 48 hours\n\n"
        f"Data summary:\n{summary}"
    )

    llm = _get_llm()
    try:
        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", user_content),
        ])
        analysis_text = response.content
    except Exception as exc:
        logger.exception("LLM analysis failed")
        analysis_text = f"Analysis unavailable: {exc}"

    return {**state, "analysis": analysis_text}


# ---------------------------------------------------------------------------
# Node: respond
# ---------------------------------------------------------------------------

async def respond(state: GraphState) -> GraphState:
    """Answer a follow-up question grounded in the data and analysis."""
    question = state.get("user_question", "")
    if not question:
        return state

    data = state.get("measurements")
    analysis = state.get("analysis", "")
    history = state.get("chat_history", [])

    # Build data context for the LLM
    data_context = ""
    if data:
        data_context = (
            f"City: {data.city}\n"
            f"Data summary:\n{_summarise_measurements(data.all_measurements)}"
        )

    # Assemble messages
    messages: list[tuple[str, str]] = [("system", _RESPOND_SYSTEM_PROMPT)]

    if data_context:
        messages.append(("system", f"Available data:\n{data_context}"))
    if analysis:
        messages.append(("system", f"Previous analysis:\n{analysis}"))

    for msg in history:
        messages.append((msg.role, msg.content))

    messages.append(("human", question))

    llm = _get_llm()
    try:
        response = await llm.ainvoke(messages)
        answer = response.content
    except Exception as exc:
        logger.exception("LLM respond failed")
        answer = f"Sorry, I couldn't process your question: {exc}"

    updated_history = list(history) + [
        ChatMessage(role="user", content=question),
        ChatMessage(role="assistant", content=answer),
    ]

    return {**state, "chat_history": updated_history, "user_question": ""}
