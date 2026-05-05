"""Tests for the LangGraph chain — mock Gemini, verify flow & grounding."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from src.graph.chain import build_analysis_chain, build_chat_chain, _should_respond
from src.graph.nodes import _summarise_measurements
from src.models.schemas import (
    ChatMessage,
    CityAirQuality,
    Measurement,
    Pollutant,
    StationData,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_measurement(
    value: float = 12.0,
    parameter: Pollutant = Pollutant.PM25,
    unit: str = "µg/m³",
    location_id: int = 1,
    sensor_id: int = 100,
    location_name: str = "Station A",
) -> Measurement:
    return Measurement(
        value=value,
        parameter=parameter,
        unit=unit,
        datetime_from=datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc),
        datetime_to=datetime(2024, 6, 1, 11, 0, tzinfo=timezone.utc),
        location_id=location_id,
        sensor_id=sensor_id,
        location_name=location_name,
    )


def _make_city_data(city: str = "London") -> CityAirQuality:
    return CityAirQuality(
        city=city,
        stations=[
            StationData(
                location_id=1,
                name="Station A",
                latitude=51.5,
                longitude=-0.1,
                measurements=[
                    _make_measurement(value=12.0, parameter=Pollutant.PM25),
                    _make_measurement(value=30.0, parameter=Pollutant.PM10),
                    _make_measurement(value=18.0, parameter=Pollutant.NO2),
                ],
            ),
            StationData(
                location_id=2,
                name="Station B",
                latitude=51.51,
                longitude=-0.12,
                measurements=[
                    _make_measurement(
                        value=20.0,
                        parameter=Pollutant.PM25,
                        location_id=2,
                        sensor_id=200,
                        location_name="Station B",
                    ),
                ],
            ),
        ],
    )


def _fake_llm_response(content: str) -> AsyncMock:
    """Build a mock LLM that returns the given content."""
    mock_response = AsyncMock()
    mock_response.content = content
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


# ---------------------------------------------------------------------------
# _should_respond routing
# ---------------------------------------------------------------------------

class TestShouldRespond:
    def test_routes_to_respond_when_question_present(self):
        state = {"user_question": "Is PM2.5 safe?"}
        assert _should_respond(state) == "respond"

    def test_routes_to_end_when_no_question(self):
        from langgraph.graph import END
        assert _should_respond({}) == END
        assert _should_respond({"user_question": ""}) == END


# ---------------------------------------------------------------------------
# _summarise_measurements
# ---------------------------------------------------------------------------

class TestSummariseMeasurements:
    def test_empty_measurements(self):
        assert _summarise_measurements([]) == "No measurements available."

    def test_summary_contains_pollutant_stats(self):
        ms = [
            _make_measurement(value=10.0, parameter=Pollutant.PM25),
            _make_measurement(value=20.0, parameter=Pollutant.PM25),
        ]
        result = _summarise_measurements(ms)
        assert "PM25" in result
        assert "min=10.0" in result
        assert "max=20.0" in result
        assert "avg=15.0" in result
        assert "2 readings" in result

    def test_summary_lists_station_names(self):
        ms = [
            _make_measurement(value=5.0, location_name="Alpha"),
            _make_measurement(value=8.0, location_name="Beta"),
        ]
        result = _summarise_measurements(ms)
        assert "Alpha" in result
        assert "Beta" in result


# ---------------------------------------------------------------------------
# Analysis chain (retrieve → analyze → END)
# ---------------------------------------------------------------------------

class TestAnalysisChain:
    async def test_analysis_chain_produces_analysis(self):
        """Full chain: mock OpenAQ + mock LLM → state contains analysis."""
        city_data = _make_city_data()
        mock_llm = _fake_llm_response("Air quality in London is moderate.")

        with (
            patch(
                "src.graph.nodes.fetch_city_data",
                new_callable=AsyncMock,
                return_value=city_data,
            ),
            patch("src.graph.nodes._get_llm", return_value=mock_llm),
        ):
            chain = build_analysis_chain()
            result = await chain.ainvoke({"city": "London"})

        assert result["measurements"] == city_data
        assert result["analysis"] == "Air quality in London is moderate."
        assert result["error"] == ""

    async def test_analysis_chain_handles_fetch_error(self):
        """Retrieve failure → empty analysis, error message populated."""
        with patch(
            "src.graph.nodes.fetch_city_data",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API down"),
        ):
            chain = build_analysis_chain()
            result = await chain.ainvoke({"city": "London"})

        assert result["measurements"] is None
        assert result["analysis"] == ""
        assert "API down" in result["error"]

    async def test_analysis_chain_handles_llm_error(self):
        """LLM failure → analysis contains error message."""
        city_data = _make_city_data()
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        with (
            patch(
                "src.graph.nodes.fetch_city_data",
                new_callable=AsyncMock,
                return_value=city_data,
            ),
            patch("src.graph.nodes._get_llm", return_value=mock_llm),
        ):
            chain = build_analysis_chain()
            result = await chain.ainvoke({"city": "London"})

        assert "Analysis unavailable" in result["analysis"]

    async def test_analysis_sends_data_to_llm(self):
        """Verify the LLM receives the measurement summary in its prompt."""
        city_data = _make_city_data()
        mock_llm = _fake_llm_response("Analysis text.")

        with (
            patch(
                "src.graph.nodes.fetch_city_data",
                new_callable=AsyncMock,
                return_value=city_data,
            ),
            patch("src.graph.nodes._get_llm", return_value=mock_llm),
        ):
            chain = build_analysis_chain()
            await chain.ainvoke({"city": "London"})

        call_args = mock_llm.ainvoke.call_args[0][0]
        # The human message should contain station/measurement data
        human_msg = call_args[-1][1]
        assert "London" in human_msg
        assert "PM25" in human_msg
        assert "Station A" in human_msg


# ---------------------------------------------------------------------------
# Chat chain (conditional → respond → END)
# ---------------------------------------------------------------------------

class TestChatChain:
    async def test_chat_chain_responds_to_question(self):
        """Follow-up question → respond node produces answer."""
        city_data = _make_city_data()
        mock_llm = _fake_llm_response("PM2.5 is at 12 µg/m³, below WHO guideline.")

        with patch("src.graph.nodes._get_llm", return_value=mock_llm):
            chain = build_chat_chain()
            result = await chain.ainvoke({
                "measurements": city_data,
                "analysis": "Previous analysis.",
                "user_question": "What is PM2.5?",
                "chat_history": [],
            })

        assert result["user_question"] == ""
        assert len(result["chat_history"]) == 2
        assert result["chat_history"][0].role == "user"
        assert result["chat_history"][0].content == "What is PM2.5?"
        assert result["chat_history"][1].role == "assistant"
        assert "12 µg/m³" in result["chat_history"][1].content

    async def test_chat_chain_skips_when_no_question(self):
        """No user_question → chain ends immediately, state unchanged."""
        chain = build_chat_chain()
        result = await chain.ainvoke({
            "measurements": _make_city_data(),
            "analysis": "Some analysis.",
            "user_question": "",
            "chat_history": [],
        })

        assert result.get("chat_history") == []

    async def test_chat_chain_preserves_history(self):
        """Existing chat history is preserved and extended."""
        city_data = _make_city_data()
        existing = [
            ChatMessage(role="user", content="First question"),
            ChatMessage(role="assistant", content="First answer"),
        ]
        mock_llm = _fake_llm_response("Follow-up answer.")

        with patch("src.graph.nodes._get_llm", return_value=mock_llm):
            chain = build_chat_chain()
            result = await chain.ainvoke({
                "measurements": city_data,
                "analysis": "Analysis.",
                "user_question": "Second question",
                "chat_history": existing,
            })

        assert len(result["chat_history"]) == 4
        assert result["chat_history"][2].content == "Second question"
        assert result["chat_history"][3].content == "Follow-up answer."

    async def test_chat_chain_passes_history_to_llm(self):
        """Verify the LLM receives chat history as context."""
        city_data = _make_city_data()
        existing = [
            ChatMessage(role="user", content="Previous Q"),
            ChatMessage(role="assistant", content="Previous A"),
        ]
        mock_llm = _fake_llm_response("New answer.")

        with patch("src.graph.nodes._get_llm", return_value=mock_llm):
            chain = build_chat_chain()
            await chain.ainvoke({
                "measurements": city_data,
                "analysis": "Analysis.",
                "user_question": "New question",
                "chat_history": existing,
            })

        call_args = mock_llm.ainvoke.call_args[0][0]
        # Should contain the history messages + the new question
        msg_contents = [msg[1] for msg in call_args]
        assert "Previous Q" in msg_contents
        assert "Previous A" in msg_contents
        assert "New question" in msg_contents


# ---------------------------------------------------------------------------
# Grounding tests — model should only use provided data
# ---------------------------------------------------------------------------

class TestGrounding:
    async def test_analysis_prompt_contains_who_guidelines(self):
        """System prompt sent to LLM includes WHO guideline values."""
        city_data = _make_city_data()
        mock_llm = _fake_llm_response("Analysis.")

        with (
            patch(
                "src.graph.nodes.fetch_city_data",
                new_callable=AsyncMock,
                return_value=city_data,
            ),
            patch("src.graph.nodes._get_llm", return_value=mock_llm),
        ):
            chain = build_analysis_chain()
            await chain.ainvoke({"city": "London"})

        call_args = mock_llm.ainvoke.call_args[0][0]
        system_msg = call_args[0][1]
        assert "15 µg/m³" in system_msg  # PM2.5 guideline
        assert "45 µg/m³" in system_msg  # PM10 guideline
        assert "ONLY use the data provided" in system_msg

    async def test_respond_prompt_enforces_grounding(self):
        """Respond system prompt instructs LLM to stick to provided data."""
        city_data = _make_city_data()
        mock_llm = _fake_llm_response("Answer.")

        with patch("src.graph.nodes._get_llm", return_value=mock_llm):
            chain = build_chat_chain()
            await chain.ainvoke({
                "measurements": city_data,
                "analysis": "Analysis.",
                "user_question": "Tell me about weather",
                "chat_history": [],
            })

        call_args = mock_llm.ainvoke.call_args[0][0]
        system_msg = call_args[0][1]
        assert "ONLY" in system_msg
        assert "Do NOT" in system_msg

    async def test_respond_includes_data_context(self):
        """Respond node passes the measurement data as context to the LLM."""
        city_data = _make_city_data()
        mock_llm = _fake_llm_response("Answer.")

        with patch("src.graph.nodes._get_llm", return_value=mock_llm):
            chain = build_chat_chain()
            await chain.ainvoke({
                "measurements": city_data,
                "analysis": "Prior analysis text.",
                "user_question": "Is PM2.5 safe?",
                "chat_history": [],
            })

        call_args = mock_llm.ainvoke.call_args[0][0]
        all_text = " ".join(msg[1] for msg in call_args)
        assert "London" in all_text
        assert "PM25" in all_text
        assert "Prior analysis text." in all_text
