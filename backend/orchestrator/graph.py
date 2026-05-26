# import asyncio
# from typing import TypedDict
# from langgraph.graph import StateGraph, END
# from backend.models.schemas import AgentReview, ReviewResponse
# from backend.agents.security_agent import run_security_agent
# from backend.agents.performance_agent import run_performance_agent
# from backend.agents.logic_agent import run_logic_agent
# from backend.agents.style_agent import run_style_agent
# from backend.utils.llm import generate


# class ReviewState(TypedDict):
#     code: str
#     security: AgentReview | None
#     performance: AgentReview | None
#     logic: AgentReview | None
#     style: AgentReview | None
#     final_recommendation: str
#     overall_score: int
#     total_issues: int


# async def run_all_agents(state: ReviewState) -> ReviewState:
#     """
#     Run agents sequentially with delay to respect free-tier RPM limits.
#     Each agent is independent — a failure in one doesn't block the others.
#     """
#     code = state["code"]

#     async def safe_run(agent_fn, name: str) -> AgentReview:
#         try:
#             return await agent_fn(code)
#         except Exception as e:
#             print(f"[{name}] Agent failed entirely: {e}")
#             # Return a minimal valid AgentReview so the pipeline continues
#             return AgentReview(
#                 agent_name=name,
#                 issues=[],
#                 summary=f"{name} encountered an error: {str(e)[:100]}",
#                 score=50,
#             )

#     security = await safe_run(run_security_agent, "SecurityAgent")
#     await asyncio.sleep(4)

#     performance = await safe_run(run_performance_agent, "PerformanceAgent")
#     await asyncio.sleep(4)

#     logic = await safe_run(run_logic_agent, "LogicAgent")
#     await asyncio.sleep(4)

#     style = await safe_run(run_style_agent, "StyleAgent")

#     return {
#         **state,
#         "security": security,
#         "performance": performance,
#         "logic": logic,
#         "style": style,
#     }


# async def synthesize_results(state: ReviewState) -> ReviewState:
#     """Merge all agent outputs into a final recommendation."""
#     security    = state["security"]
#     performance = state["performance"]
#     logic       = state["logic"]
#     style       = state["style"]

#     total_issues = (
#         len(security.issues) + len(performance.issues)
#         + len(logic.issues) + len(style.issues)
#     )
#     overall_score = (
#         security.score + performance.score + logic.score + style.score
#     ) // 4

#     prompt = f"""You are a Senior Engineering Lead synthesizing a multi-agent code review.

# Agent Results:
# - Security ({security.score}/100): {security.summary}
# - Performance ({performance.score}/100): {performance.summary}
# - Logic ({logic.score}/100): {logic.summary}
# - Style ({style.score}/100): {style.summary}

# Total issues found: {total_issues} | Overall score: {overall_score}/100

# Write a concise 3-4 sentence final recommendation:
# 1. State if the code is ready to merge (yes/no/conditional)
# 2. Highlight the top 2 most critical concerns
# 3. Give a clear actionable verdict

# Return plain text only, no JSON, no markdown headers."""

#     try:
#         recommendation = await generate(prompt)
#     except Exception as e:
#         recommendation = (
#             f"Review complete. Overall score: {overall_score}/100. "
#             f"Found {total_issues} issues across all agents. "
#             "Please review individual agent findings above."
#         )
#         print(f"[Synthesizer] Failed to generate recommendation: {e}")

#     return {
#         **state,
#         "final_recommendation": recommendation,
#         "overall_score": overall_score,
#         "total_issues": total_issues,
#     }


# def build_review_graph():
#     graph = StateGraph(ReviewState)
#     graph.add_node("run_agents", run_all_agents)
#     graph.add_node("synthesize", synthesize_results)
#     graph.set_entry_point("run_agents")
#     graph.add_edge("run_agents", "synthesize")
#     graph.add_edge("synthesize", END)
#     return graph.compile()


# async def run_review(code: str) -> ReviewResponse:
#     graph = build_review_graph()
#     initial_state: ReviewState = {
#         "code": code,
#         "security": None,
#         "performance": None,
#         "logic": None,
#         "style": None,
#         "final_recommendation": "",
#         "overall_score": 0,
#         "total_issues": 0,
#     }
#     result = await graph.ainvoke(initial_state)
#     return ReviewResponse(
#         security=result["security"],
#         performance=result["performance"],
#         logic=result["logic"],
#         style=result["style"],
#         final_recommendation=result["final_recommendation"],
#         overall_score=result["overall_score"],
#         total_issues=result["total_issues"],
#     )

import asyncio
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
    """
    Run agents sequentially.
    Sleep between agents reduced to 2s — enough to avoid RPM burst,
    short enough to not frustrate users.
    """
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
    await asyncio.sleep(2)   # was 4s
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
3. Give a clear actionable verdict

Return plain text only, no JSON, no markdown headers."""

    try:
        recommendation = await generate(prompt)
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