from backend.utils.llm import generate, safe_parse
from backend.models.schemas import AgentReview, Issue

PROMPT_TEMPLATE = """You are an expert Code Style & Quality Reviewer. Analyze ONLY for style issues: naming conventions, PEP8, DRY violations, missing type hints, poor documentation, overly complex functions.

Return raw JSON only (no markdown, no backticks):
{{"agent_name":"StyleAgent","issues":[{{"line":"line number or null","description":"issue description","severity":"critical|high|medium|low|info","suggestion":"fix"}}],"summary":"brief assessment","score":85}}

score 0-100 where 100 = perfectly styled.

Code:
{code}"""


async def run_style_agent(code: str) -> AgentReview:
    raw = await generate(PROMPT_TEMPLATE.replace("{code}", code))

    data = safe_parse(raw, "StyleAgent")

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