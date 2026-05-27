from backend.utils.llm import generate, safe_parse
from backend.models.schemas import AgentReview, Issue

PROMPT_TEMPLATE = """You are a Code Style Reviewer. Find ONLY style issues: naming conventions, PEP8, DRY violations, missing type hints, poor documentation.

Respond with ONLY a JSON object. No extra text, no markdown fences, no backticks.
Keep descriptions under 20 words. Keep suggestions under 15 words.

{{"agent_name":"StyleAgent","issues":[{{"line":"line number or null","description":"issue","severity":"critical|high|medium|low|info","suggestion":"fix"}}],"summary":"one sentence max","score":85}}

Code to review:
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
        score=int(str(data["score"]).strip()) if str(data["score"]).strip().isdigit() else 50,
    )