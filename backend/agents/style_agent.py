import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.models.schemas import AgentReview, Issue

SYSTEM_PROMPT = """You are an expert Code Style & Quality Reviewer with deep knowledge of:
- PEP8, Google style guides, language idioms
- Code readability, naming conventions
- DRY principle, code duplication
- Documentation, comments, type hints
- Code organization, function length, complexity

Analyze the provided code ONLY for style and code quality issues.
Return a JSON object with this exact structure:
{
  "agent_name": "StyleAgent",
  "issues": [
    {
      "line": "line number or null",
      "description": "what the style issue is",
      "severity": "critical|high|medium|low|info",
      "suggestion": "how to improve it"
    }
  ],
  "summary": "brief overall style assessment",
  "score": 85
}
score is 0-100 where 100 is perfectly styled. Return ONLY valid JSON, no markdown."""


async def run_style_agent(code: str, llm: ChatGoogleGenerativeAI) -> AgentReview:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Review this code for style and quality issues:\n\n{code}"),
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