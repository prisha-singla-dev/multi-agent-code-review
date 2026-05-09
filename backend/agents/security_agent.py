import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.models.schemas import AgentReview, Issue, Severity

SYSTEM_PROMPT = """You are an expert Security Code Reviewer with deep knowledge of:
- OWASP Top 10 vulnerabilities
- SQL injection, XSS, CSRF, authentication flaws
- Insecure deserialization, hardcoded secrets
- Dependency vulnerabilities, input validation

Analyze the provided code ONLY for security issues.
Return a JSON object with this exact structure:
{
  "agent_name": "SecurityAgent",
  "issues": [
    {
      "line": "line number or null",
      "description": "what the issue is",
      "severity": "critical|high|medium|low|info",
      "suggestion": "how to fix it"
    }
  ],
  "summary": "brief overall security assessment",
  "score": 85
}
score is 0-100 where 100 is perfectly secure. Return ONLY valid JSON, no markdown."""


async def run_security_agent(code: str, llm: ChatGoogleGenerativeAI) -> AgentReview:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Review this code for security issues:\n\n{code}"),
    ]
    response = await llm.ainvoke(messages)
    raw = response.content.strip()
    # Strip markdown fences if present
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