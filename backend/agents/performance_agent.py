from backend.utils.llm import generate, safe_parse
from backend.models.schemas import AgentReview, Issue

PROMPT_TEMPLATE = """You are a Performance Code Reviewer. Find the top 5 most critical performance issues only.

Return ONLY a raw JSON object. No markdown. No backticks. No explanation. Just JSON.

Format exactly:
{{"agent_name":"PerformanceAgent","issues":[{{"line":"line number or null","description":"brief issue description under 15 words","severity":"critical|high|medium|low|info","suggestion":"brief fix under 15 words"}}],"summary":"one sentence summary","score":50}}

score: 0-100 (100 = perfectly optimized)

Code to review:
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
        score=int(data["score"]) if str(data.get("score", 50)).lstrip('-').isdigit() else 50,
    )