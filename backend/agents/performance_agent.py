from backend.utils.llm import generate, safe_parse
from backend.models.schemas import AgentReview, Issue

PROMPT_TEMPLATE = """You are an expert Performance Code Reviewer. Analyze ONLY for performance issues: Big O complexity, N+1 queries, memory leaks, inefficient loops, missing caching.

Return raw JSON only (no markdown, no backticks):
{{"agent_name":"PerformanceAgent","issues":[{{"line":"line number or null","description":"issue description","severity":"critical|high|medium|low|info","suggestion":"fix"}}],"summary":"brief assessment","score":85}}

score 0-100 where 100 = perfectly optimized.

Code:
{code}"""


async def run_performance_agent(code: str) -> AgentReview:
    raw = await generate(PROMPT_TEMPLATE.replace("{code}", code))

    data = safe_parse(raw, "PerformanceAgent")

    issues = []
    for i in data.get("issues", []):
        try:
            issues.append(Issue(**{k: v for k, v in i.items() if k in Issue.model_fields}))
        except Exception:
            pass

    return AgentReview(
        agent_name=data["agent_name"],
        issues=issues,
        summary=data["summary"],
        score=int(data["score"]) if str(data["score"]).isdigit() else 50,
    )