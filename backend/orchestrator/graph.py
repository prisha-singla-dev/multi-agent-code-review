import asyncio
import os
from typing import TypedDict

from langgraph.graph import StateGraph, END

from backend.models.schemas import AgentReview, ReviewResponse
from backend.agents.security_agent import run_security_agent
from backend.agents.performance_agent import run_performance_agent
from backend.agents.logic_agent import run_logic_agent
from backend.agents.style_agent import run_style_agent
from backend.utils.llm import generate


class ReviewState(TypedDict):
    code: str
    security: AgentReview | None
    performance: AgentReview | None
    logic: AgentReview | None
    style: AgentReview | None
    final_recommendation: str
    overall_score: int
    total_issues: int


async def run_all_agents(state: ReviewState) -> ReviewState:
    """Run agents sequentially to respect free-tier RPM limits."""
    code = state["code"]

    security    = await run_security_agent(code)
    performance = await run_performance_agent(code)
    logic       = await run_logic_agent(code)
    style       = await run_style_agent(code)

    return {
        **state,
        "security": security,
        "performance": performance,
        "logic": logic,
        "style": style,
    }


async def synthesize_results(state: ReviewState) -> ReviewState:
    """Merge all agent outputs into a final recommendation."""
    security    = state["security"]
    performance = state["performance"]
    logic       = state["logic"]
    style       = state["style"]

    total_issues = (
        len(security.issues) + len(performance.issues)
        + len(logic.issues) + len(style.issues)
    )
    overall_score = (
        security.score + performance.score + logic.score + style.score
    ) // 4

    prompt = f"""You are a Senior Engineering Lead synthesizing a multi-agent code review.

Agent Results:
- Security ({security.score}/100): {security.summary}
- Performance ({performance.score}/100): {performance.summary}
- Logic ({logic.score}/100): {logic.summary}
- Style ({style.score}/100): {style.summary}

Total issues: {total_issues} | Overall score: {overall_score}/100

Write a concise 3-4 sentence final recommendation:
1. State if the code is ready to merge (yes/no/conditional)
2. Highlight the top 2 most critical concerns
3. Give a clear actionable verdict"""

    recommendation = await generate(prompt)

    return {
        **state,
        "final_recommendation": recommendation,
        "overall_score": overall_score,
        "total_issues": total_issues,
    }


def build_review_graph():
    graph = StateGraph(ReviewState)
    graph.add_node("run_agents", run_all_agents)
    graph.add_node("synthesize", synthesize_results)
    graph.set_entry_point("run_agents")
    graph.add_edge("run_agents", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


async def run_review(code: str) -> ReviewResponse:
    graph = build_review_graph()
    initial_state: ReviewState = {
        "code": code,
        "security": None,
        "performance": None,
        "logic": None,
        "style": None,
        "final_recommendation": "",
        "overall_score": 0,
        "total_issues": 0,
    }
    result = await graph.ainvoke(initial_state)
    return ReviewResponse(
        security=result["security"],
        performance=result["performance"],
        logic=result["logic"],
        style=result["style"],
        final_recommendation=result["final_recommendation"],
        overall_score=result["overall_score"],
        total_issues=result["total_issues"],
    )