"""Chat interface component for air quality follow-up questions."""

from __future__ import annotations

import asyncio

import streamlit as st

from src.graph.chain import chat_chain
from src.models.schemas import ChatMessage, CityAirQuality


def _run_chat(
    question: str,
    data: CityAirQuality,
    analysis: str,
    history: list[ChatMessage],
) -> list[ChatMessage]:
    """Send a follow-up question through the chat chain and return updated history."""
    result = asyncio.run(
        chat_chain.ainvoke({
            "city": data.city,
            "measurements": data,
            "analysis": analysis,
            "user_question": question,
            "chat_history": history,
        })
    )
    return result.get("chat_history", history)


def render_chat(data: CityAirQuality, analysis: str) -> None:
    """Render the chat interface for follow-up questions."""
    # --- Init session state ---
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.divider()

    # --- Header row: title + clear button ---
    col_title, col_clear = st.columns([4, 1])
    with col_title:
        st.subheader("Ask a follow-up question")
    with col_clear:
        if st.session_state.chat_history and st.button(
            "Clear chat", use_container_width=True
        ):
            st.session_state.chat_history = []
            st.rerun()

    # --- Data context indicator ---
    st.caption(
        f"🗂️ Context: **{data.city}** · "
        f"{len(data.stations)} station(s) · "
        f"{len(data.all_measurements)} measurements · "
        f"{'✅ Analysis loaded' if analysis else '⚠️ No analysis available'}"
    )
    st.caption(
        "The assistant answers using only the available measurements and analysis."
    )

    # --- Display chat history ---
    for msg in st.session_state.chat_history:
        with st.chat_message(msg.role):
            st.markdown(msg.content)

    # --- Chat input ---
    if question := st.chat_input("e.g. Is PM2.5 above safe levels?"):
        # Show user message immediately
        with st.chat_message("user"):
            st.markdown(question)

        # Get LLM response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                st.session_state.chat_history = _run_chat(
                    question=question,
                    data=data,
                    analysis=analysis,
                    history=st.session_state.chat_history,
                )
            st.markdown(st.session_state.chat_history[-1].content)
