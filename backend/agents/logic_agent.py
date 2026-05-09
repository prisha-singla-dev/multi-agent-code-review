import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.models.schemas import AgentReview, Issue

SYSTEM_PROMPT = """You are an expert Logic & Correctness Code Reviewer with deep knowledge of:
- Business logic errors and edge cases
- Off-by-one errors, null pointer issues
- Race conditions, concurrency bugs
- Incorrect error handling, silent failures
- Missing validation, wrong assumptions

Analyze the provided code ONLY for logic and correctness issues.
Return a JSON object with this exact structure:
{
  "agent_name": "LogicAgent",
  "issues": [
    {
      "line": "line number or null",
      "description": "what the logic issue is",
      "severity": "critical|high|medium|low|info",
      "suggestion": "how to fix it"
    }
  ],
  "summary": "brief overall logic assessment",
  "score": 85
}
score is 0-100 where 100 is logically perfect. Return ONLY valid JSON, no markdown."""


async def run_logic_agent(code: str, llm: ChatGoogleGenerativeAI) -> AgentReview:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Review this code for logic and correctness issues:\n\n{code}"),
    ]
    response = await llm.ainvoke(messages)
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())
    issues = [Issue(**i) for i in data.get("issues", [])]
    return AgentReview(
        agent_name=data["agent_name"],
        issues=issues,
        summary=data["summary"],
        score=data["score"],
    )