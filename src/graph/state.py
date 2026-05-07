"""LangGraph state definition for the air quality analysis chain."""

from __future__ import annotations

from typing import TypedDict

from src.models.schemas import ChatMessage, CityAirQuality


class GraphState(TypedDict, total=False):
    """State flowing through the LangGraph chain.

    Attributes:
        city: Name of the UK city being analysed.
        hours: Look-back window in hours.
        granularity: 'hours' or 'days' — drives OpenAQ endpoint selection.
        range_label: Human-readable label for the range (used in prompts/UI).
        measurements: Validated air quality data fetched from OpenAQ.
        analysis: LLM-generated summary of the air quality data.
        chat_history: Conversation history for follow-up questions.
        user_question: The latest follow-up question from the user.
        error: Optional error message if a node fails.
    """

    city: str
    hours: int
    granularity: str
    range_label: str
    measurements: CityAirQuality | None
    analysis: str
    chat_history: list[ChatMessage]
    user_question: str
    error: str
