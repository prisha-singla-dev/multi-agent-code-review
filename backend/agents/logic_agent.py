import json
from backend.utils.llm import generate
from backend.models.schemas import AgentReview, Issue
from backend.utils.llm import generate, extract_json

PROMPT_TEMPLATE = """You are an expert Logic & Correctness Code Reviewer. Analyze ONLY for logic issues: edge cases, off-by-one errors, null/None handling, race conditions, wrong error handling, silent failures.

Return raw JSON only (no markdown, no backticks):
{{"agent_name":"LogicAgent","issues":[{{"line":"line number or null","description":"issue description","severity":"critical|high|medium|low|info","suggestion":"fix"}}],"summary":"brief assessment","score":85}}

score 0-100 where 100 = logically perfect.

Code:
{code}"""

# PROMPT_TEMPLATE = """Logic review. Find ONLY logic bugs (edge cases, off-by-one, null handling, wrong assumptions).

# Return raw JSON only, no markdown:
# {"agent_name":"LogicAgent","issues":[{"line":"line or null","description":"issue","severity":"critical|high|medium|low|info","suggestion":"fix"}],"summary":"one sentence","score":85}

# Code:
# {code}"""

# async def run_logic_agent(code: str) -> AgentReview:
#     raw = await generate(PROMPT_TEMPLATE.format(code=code))
#     raw = raw.strip()
#     if raw.startswith("```"):
#         raw = raw.split("```")[1]
#         if raw.startswith("json"):
#             raw = raw[4:]
#         raw = raw.strip()
#     if raw.endswith("```"):
#         raw = raw[:-3].strip()
#     data = json.loads(raw)
#     return AgentReview(
#         agent_name=data["agent_name"],
#         issues=[Issue(**i) for i in data.get("issues", [])],
#         summary=data["summary"],
#         score=data["score"],
#     )

async def run_logic_agent(code: str) -> AgentReview:
    raw = await generate(PROMPT_TEMPLATE.format(code=code))
    raw = raw.strip()
    
    
    # Strip markdown fences robustly
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    
    # Extract JSON object if there's text around it
    start = raw.find("{")
    end = raw.rfind("}") + 1
    raw = raw[start:end]
    
    data = json.loads(extract_json(raw))
    issues = [Issue(**i) for i in data.get("issues", [])]
    return AgentReview(
        agent_name=data["agent_name"],
        issues=issues,
        summary=data["summary"],
        score=data["score"],
    )