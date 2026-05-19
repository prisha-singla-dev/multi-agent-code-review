from backend.utils.llm import generate, safe_parse
from backend.models.schemas import AgentReview, Issue

PROMPT_TEMPLATE = """You are an expert Security Code Reviewer. Analyze ONLY for security issues: SQL injection, XSS, auth flaws, hardcoded secrets, OWASP Top 10.

Return raw JSON only (no markdown, no backticks):
{{"agent_name":"SecurityAgent","issues":[{{"line":"line number or null","description":"issue description","severity":"critical|high|medium|low|info","suggestion":"fix"}}],"summary":"brief assessment","score":85}}

score 0-100 where 100 = perfectly secure.

Code:
{code}"""


async def run_security_agent(code: str) -> AgentReview:
    # FIX 1: .replace() instead of .format() — safe when code contains { or }
    raw = await generate(PROMPT_TEMPLATE.replace("{code}", code))

    # FIX 2: safe_parse never raises — handles truncated/malformed JSON
    data = safe_parse(raw, "SecurityAgent")

    # FIX 3: Issue(**i) wrapped in try/except — skips malformed issue dicts
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