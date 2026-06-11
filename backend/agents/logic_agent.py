from backend.utils.llm import generate, safe_parse
from backend.models.schemas import AgentReview, Issue

PROMPT_TEMPLATE = """You are a Logic & Correctness Code Reviewer. Find up to 5 critical logic issues.

Respond with ONLY this JSON structure, no other text:
{{"agent_name":"LogicAgent","issues":[{{"line":"line number or null","description":"under 12 words","severity":"critical|high|medium|low|info","suggestion":"under 12 words"}}],"summary":"one sentence","score":65}}

Score 0-100. 100 means logically perfect.

Code:
{code}"""


def _coerce_issue(i: dict) -> Issue | None:
    try:
        line_val = i.get("line")
        if line_val is not None:
            line_val = str(line_val)

        return Issue(
            line=line_val,
            description=str(i.get("description", "")).strip() or "No description provided",
            severity=str(i.get("severity", "info")).lower().strip(),
            suggestion=str(i.get("suggestion", "")).strip() or "No suggestion provided",
        )
    except Exception as e:
        print(f"[LogicAgent] _coerce_issue failed for {i}: {e}")
        return None


async def run_logic_agent(code: str) -> AgentReview:
    raw = await generate(PROMPT_TEMPLATE.replace("{code}", code))
    data = safe_parse(raw, "LogicAgent")

    raw_issues = data.get("issues", [])
    print(f"[LogicAgent] Parsed {len(raw_issues)} raw issues from LLM")

    issues = []
    for i in raw_issues:
        if not isinstance(i, dict):
            print(f"[LogicAgent] Skipping non-dict issue: {i}")
            continue
        issue = _coerce_issue(i)
        if issue:
            issues.append(issue)

    print(f"[LogicAgent] Successfully built {len(issues)} Issue objects")

    return AgentReview(
        agent_name=data["agent_name"],
        issues=issues,
        summary=data["summary"],
        score=int(data["score"]) if str(data.get("score", 50)).lstrip("-").isdigit() else 50,
    )