from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from typing import Any

from ..agents.planner import planner_node
from ..agents.searcher import searcher_node
from ..agents.retriever import retriever_node
from ..agents.summarizer import summarizer_node
from ..agents.synthesizer import synthesizer_node
from ..agents.critic import critic_node
from ..agents.presenter import presenter_node

def build_research_graph():
    def merge_state(left: dict, right: dict) -> dict:
        """Merge right into left, preserving all keys"""
        return {**left, **right}
    
    g = StateGraph(dict)
    
    g.add_node("planner", planner_node)
    g.add_node("searcher", searcher_node)
    g.add_node("retriever", retriever_node)
    g.add_node("summarizer", summarizer_node)
    g.add_node("synthesizer", synthesizer_node)
    g.add_node("critic", critic_node)
    g.add_node("presenter", presenter_node)

    g.add_edge(START, "planner")
    g.add_edge("planner", "searcher")
    g.add_edge("searcher", "retriever")
    g.add_edge("retriever", "summarizer")
    g.add_edge("summarizer", "synthesizer")
    g.add_edge("synthesizer", "critic")
    g.add_edge("critic", "presenter")
    g.add_edge("presenter", END)

    return g.compile()