import json
from backend.utils.llm import generate
from backend.models.schemas import AgentReview, Issue

PROMPT_TEMPLATE = """You are an expert Code Style & Quality Reviewer. Analyze ONLY for style issues: naming conventions, PEP8, DRY violations, missing type hints, poor documentation, overly complex functions.

Return raw JSON only (no markdown, no backticks):
{{"agent_name":"StyleAgent","issues":[{{"line":"line number or null","description":"issue description","severity":"critical|high|medium|low|info","suggestion":"fix"}}],"summary":"brief assessment","score":85}}

score 0-100 where 100 = perfectly styled.

Code:
{code}"""


async def run_style_agent(code: str) -> AgentReview:
    raw = await generate(PROMPT_TEMPLATE.format(code=code))
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    data = json.loads(raw)
    return AgentReview(
        agent_name=data["agent_name"],
        issues=[Issue(**i) for i in data.get("issues", [])],
        summary=data["summary"],
        score=data["score"],
    )