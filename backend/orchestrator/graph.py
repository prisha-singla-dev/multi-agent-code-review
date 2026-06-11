import asyncio
import json
import re
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
    code = state["code"]

    async def safe_run(agent_fn, name: str) -> AgentReview:
        try:
            return await agent_fn(code)
        except Exception as e:
            print(f"[{name}] Agent failed: {e}")
            return AgentReview(
                agent_name=name,
                issues=[],
                summary=f"{name} encountered an error: {str(e)[:100]}",
                score=50,
            )

    security    = await safe_run(run_security_agent,    "SecurityAgent")
    await asyncio.sleep(2)
    performance = await safe_run(run_performance_agent, "PerformanceAgent")
    await asyncio.sleep(2)
    logic       = await safe_run(run_logic_agent,       "LogicAgent")
    await asyncio.sleep(2)
    style       = await safe_run(run_style_agent,       "StyleAgent")

    return {
        **state,
        "security":    security,
        "performance": performance,
        "logic":       logic,
        "style":       style,
    }


def _clean_recommendation_text(text: str) -> str:
    """
    The synthesizer sometimes still gets JSON-wrapped output even with
    json_mode=False (model habit). This strips JSON wrapping if present,
    extracting just the recommendation text.
    """
    text = text.strip()

    # If it looks like JSON, try to extract the actual text field
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                # Try common key names
                for key in ("recommendation", "final_recommendation", "summary", "text"):
                    if key in parsed and isinstance(parsed[key], str):
                        return parsed[key].strip()
        except json.JSONDecodeError:
            pass

    # Strip markdown fences if present
    if "```" in text:
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```", "", text)
        text = text.strip()

    # Strip surrounding quotes if the whole thing is quoted
    if len(text) > 1 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1].strip()

    return text


async def synthesize_results(state: ReviewState) -> ReviewState:
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

    prompt = f"""You are a Senior Engineering Lead. Write a 3-4 sentence final recommendation for this code review.

Agent Results:
- Security ({security.score}/100): {security.summary}
- Performance ({performance.score}/100): {performance.summary}
- Logic ({logic.score}/100): {logic.summary}
- Style ({style.score}/100): {style.summary}

Total issues: {total_issues} | Overall score: {overall_score}/100

Write plain text only. State if ready to merge, top 2 concerns, and a clear verdict.
Do NOT use JSON. Do NOT use markdown. Just plain English sentences."""

    try:
        # KEY FIX: json_mode=False so Gemini doesn't wrap this in JSON
        recommendation = await generate(prompt, json_mode=False)
        recommendation = _clean_recommendation_text(recommendation)
    except Exception as e:
        recommendation = (
            f"Review complete. Overall score: {overall_score}/100. "
            f"Found {total_issues} issues across all agents. "
            "Please review individual agent findings above."
        )
        print(f"[Synthesizer] Failed: {e}")

    return {
        **state,
        "final_recommendation": recommendation,
        "overall_score":        overall_score,
        "total_issues":         total_issues,
    }


def build_review_graph():
    graph = StateGraph(ReviewState)
    graph.add_node("run_agents",  run_all_agents)
    graph.add_node("synthesize",  synthesize_results)
    graph.set_entry_point("run_agents")
    graph.add_edge("run_agents", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


async def run_review(code: str) -> ReviewResponse:
    graph = build_review_graph()
    initial_state: ReviewState = {
        "code":                 code,
        "security":             None,
        "performance":          None,
        "logic":                None,
        "style":                None,
        "final_recommendation": "",
        "overall_score":        0,
        "total_issues":         0,
    }
    result = await graph.ainvoke(initial_state)
    return ReviewResponse(
        security=            result["security"],
        performance=         result["performance"],
        logic=               result["logic"],
        style=               result["style"],
        final_recommendation=result["final_recommendation"],
        overall_score=       result["overall_score"],
        total_issues=        result["total_issues"],
    )