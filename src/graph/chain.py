"""LangGraph chain definition for air quality analysis."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.nodes import analyze, respond, retrieve
from src.graph.state import GraphState


def _should_respond(state: GraphState) -> str:
    """Route to 'respond' if there is a follow-up question, else end."""
    if state.get("user_question"):
        return "respond"
    return END


def build_analysis_chain() -> StateGraph:
    """Build the retrieve → analyze → END chain for initial city load.

    Returns a compiled StateGraph.
    """
    graph = StateGraph(GraphState)

    graph.add_node("retrieve", retrieve)
    graph.add_node("analyze", analyze)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", END)

    return graph.compile()


def build_chat_chain() -> StateGraph:
    """Build the respond chain for follow-up questions.

    Uses a conditional edge: if a user_question is present the graph
    routes to the respond node, otherwise it ends immediately.

    Returns a compiled StateGraph.
    """
    graph = StateGraph(GraphState)

    graph.add_node("respond", respond)

    graph.set_conditional_entry_point(_should_respond, {"respond": "respond", END: END})
    graph.add_edge("respond", END)

    return graph.compile()


# Pre-compiled graph instances for import convenience
analysis_chain = build_analysis_chain()
chat_chain = build_chat_chain()
