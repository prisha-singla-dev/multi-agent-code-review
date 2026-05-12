import asyncio
import os
from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from backend.models.schemas import AgentReview, ReviewResponse
from backend.agents.security_agent import run_security_agent
from backend.agents.performance_agent import run_performance_agent
from backend.agents.logic_agent import run_logic_agent
from backend.agents.style_agent import run_style_agent


class ReviewState(TypedDict):
    code: str
    security: AgentReview | None
    performance: AgentReview | None
    logic: AgentReview | None
    style: AgentReview | None
    final_recommendation: str
    overall_score: int
    total_issues: int


# def get_llm() -> ChatGoogleGenerativeAI:
#     return ChatGoogleGenerativeAI(
#         model="gemini-1.5-flash",
#         google_api_key=os.getenv("GEMINI_API_KEY"),
#         temperature=0.1,
#         max_retries=3
#     )

def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.1,
    )

# def get_llm() -> ChatGoogleGenerativeAI:
#     return ChatGoogleGenerativeAI(
#         model="models/gemini-1.5-flash-latest",
#         google_api_key=os.getenv("GEMINI_API_KEY"),
#         temperature=0.1,
#         max_retries=3,
#     )

# async def run_all_agents(state: ReviewState) -> ReviewState:
#     """Run all 4 agents in parallel."""
#     code = state["code"]
#     llm = get_llm()

#     security, performance, logic, style = await asyncio.gather(
#         run_security_agent(code, llm),
#         run_performance_agent(code, llm),
#         run_logic_agent(code, llm),
#         run_style_agent(code, llm),
#     )

#     return {
#         **state,
#         "security": security,
#         "performance": performance,
#         "logic": logic,
#         "style": style,
#     }

# switched to sequential only for free-tier quota management. The architecture supports true parallel execution.
async def run_all_agents(state: ReviewState) -> ReviewState:
    """Run agents sequentially to avoid rate limits on free tier."""
    code = state["code"]
    llm = get_llm()

    security    = await run_security_agent(code, llm)
    performance = await run_performance_agent(code, llm)
    logic       = await run_logic_agent(code, llm)
    style       = await run_style_agent(code, llm)

    return {
        **state,
        "security": security,
        "performance": performance,
        "logic": logic,
        "style": style,
    }


async def synthesize_results(state: ReviewState) -> ReviewState:
    """Merge all agent outputs into a final recommendation."""
    llm = get_llm()

    security = state["security"]
    performance = state["performance"]
    logic = state["logic"]
    style = state["style"]

    total_issues = (
        len(security.issues)
        + len(performance.issues)
        + len(logic.issues)
        + len(style.issues)
    )
    overall_score = (
        security.score + performance.score + logic.score + style.score
    ) // 4

    summary_prompt = f"""You are a Senior Engineering Lead synthesizing a multi-agent code review.

Agent Summaries:
- Security ({security.score}/100): {security.summary}
- Performance ({performance.score}/100): {performance.summary}
- Logic ({logic.score}/100): {logic.summary}
- Style ({style.score}/100): {style.summary}

Total issues found: {total_issues}
Overall score: {overall_score}/100

Write a concise, actionable final recommendation (3-5 sentences) that:
1. States whether the code is ready to merge
2. Highlights the top 2-3 most critical concerns
3. Gives a clear go/no-go with conditions

Be direct and professional."""

    response = await llm.ainvoke([HumanMessage(content=summary_prompt)])

    return {
        **state,
        "final_recommendation": response.content.strip(),
        "overall_score": overall_score,
        "total_issues": total_issues,
    }


def build_review_graph() -> StateGraph:
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