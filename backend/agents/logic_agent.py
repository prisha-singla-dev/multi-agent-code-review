from backend.utils.llm import generate, safe_parse
from backend.models.schemas import AgentReview, Issue

PROMPT_TEMPLATE = """You are a Logic & Correctness Code Reviewer. Find up to 5 critical logic issues.

Respond with ONLY this JSON structure, no other text:
{{"agent_name":"LogicAgent","issues":[{{"line":"line number or null","description":"under 12 words","severity":"critical|high|medium|low|info","suggestion":"under 12 words"}}],"summary":"one sentence","score":65}}

Score 0-100. 100 means logically perfect.

Code:
{code}"""


async def run_logic_agent(code: str) -> AgentReview:
    raw = await generate(PROMPT_TEMPLATE.replace("{code}", code))
    data = safe_parse(raw, "LogicAgent")
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
        score=int(data["score"]) if str(data.get("score", 50)).lstrip("-").isdigit() else 50,
    )