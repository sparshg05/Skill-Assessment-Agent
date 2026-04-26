"""
LangGraph Orchestrator — the state machine.

Graph structure:
  START
    │
    ▼
  parser_node ──────────────────────────────────────────► ERROR
    │
    ▼
  opening_message_node  ◄─────────────────────────────────┐
    │                                                      │
    ▼ (awaits human input)                                 │
  [HUMAN TURN]                                             │
    │                                                      │
    ▼                                                      │
  assessment_node ─── if phase==ASSESSING ────────────────┘
    │
    ├── if phase==ANALYSING ──► gap_analysis_node
    │                               │
    │                               ▼
    │                         learning_plan_node
    │                               │
    │                               ▼
    └──────────────────────────── END

Key: the graph is interrupted after each node that sets awaiting_human_input=True.
The API layer resumes the graph on the next candidate message.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from models import GraphState, SessionPhase
from nodes import (
    parser_node,
    generate_opening_message,
    assessment_node,
    gap_analysis_node,
    learning_plan_node,
)


# ─────────────────────────────────────────────
# Routing functions (conditional edges)
# ─────────────────────────────────────────────

def route_after_parser(state: GraphState) -> str:
    if state.phase == SessionPhase.ERROR:
        return "error_node"
    return "opening_message_node"


def route_after_assessment(state: GraphState) -> str:
    if state.phase == SessionPhase.ERROR:
        return "error_node"
    if state.phase == SessionPhase.ANALYSING:
        return "gap_analysis_node"
    # Still assessing — interrupt and wait for human
    return END


def route_after_gap_analysis(state: GraphState) -> str:
    if state.phase == SessionPhase.ERROR:
        return "error_node"
    return "learning_plan_node"


def route_after_plan(state: GraphState) -> str:
    return END


async def error_node(state: GraphState) -> GraphState:
    """Terminal error node — logs and passes through."""
    return state


# ─────────────────────────────────────────────
# Build the graph
# ─────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Construct the LangGraph StateGraph.
    Uses MemorySaver for in-process checkpointing during a session.
    """

    # LangGraph requires a TypedDict or Pydantic model with a specific schema.
    # We use a thin wrapper that maps our GraphState to LangGraph's expected format.
    from langgraph.graph.message import add_messages
    from typing import Annotated
    from typing_extensions import TypedDict

    # We use a simple dict wrapper for LangGraph compatibility
    # while keeping our clean GraphState domain model internally.

    builder = StateGraph(dict)

    # Add nodes
    builder.add_node("parser_node", _wrap(parser_node))
    builder.add_node("opening_message_node", _wrap(generate_opening_message))
    builder.add_node("assessment_node", _wrap(assessment_node))
    builder.add_node("gap_analysis_node", _wrap(gap_analysis_node))
    builder.add_node("learning_plan_node", _wrap(learning_plan_node))
    builder.add_node("error_node", _wrap(error_node))

    # Entry point
    builder.set_entry_point("parser_node")

    # Edges
    builder.add_conditional_edges("parser_node", _route_dict(route_after_parser), {
        "opening_message_node": "opening_message_node",
        "error_node": "error_node",
    })

    builder.add_edge("opening_message_node", "assessment_node")

    builder.add_conditional_edges("assessment_node", _route_dict(route_after_assessment), {
        "gap_analysis_node": "gap_analysis_node",
        "error_node": "error_node",
        END: END,
    })

    builder.add_conditional_edges("gap_analysis_node", _route_dict(route_after_gap_analysis), {
        "learning_plan_node": "learning_plan_node",
        "error_node": "error_node",
    })

    builder.add_edge("learning_plan_node", END)
    builder.add_edge("error_node", END)

    return builder


def _wrap(node_fn):
    """Wrap our GraphState-based node functions for LangGraph's dict-based state."""
    async def wrapped(state_dict: dict) -> dict:
        state = GraphState.model_validate(state_dict)
        result = await node_fn(state)
        return result.model_dump()
    return wrapped


def _route_dict(route_fn):
    """Wrap routing functions to work with dict state."""
    def wrapped(state_dict: dict) -> str:
        state = GraphState.model_validate(state_dict)
        return route_fn(state)
    return wrapped


# ─────────────────────────────────────────────
# Compiled graph singleton
# ─────────────────────────────────────────────

_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        builder = build_graph()
        _compiled_graph = builder.compile()
    return _compiled_graph