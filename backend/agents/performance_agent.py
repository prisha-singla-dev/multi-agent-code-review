import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.models.schemas import AgentReview, Issue

SYSTEM_PROMPT = """You are an expert Performance Code Reviewer with deep knowledge of:
- Time and space complexity (Big O analysis)
- Database query optimization, N+1 problems
- Memory leaks, inefficient loops, unnecessary computations
- Caching opportunities, lazy loading
- Async/concurrent programming best practices

Analyze the provided code ONLY for performance issues.
Return a JSON object with this exact structure:
{
  "agent_name": "PerformanceAgent",
  "issues": [
    {
      "line": "line number or null",
      "description": "what the performance issue is",
      "severity": "critical|high|medium|low|info",
      "suggestion": "how to optimize it"
    }
  ],
  "summary": "brief overall performance assessment",
  "score": 85
}
score is 0-100 where 100 is perfectly optimized. Return ONLY valid JSON, no markdown."""


async def run_performance_agent(code: str, llm: ChatGoogleGenerativeAI) -> AgentReview:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Review this code for performance issues:\n\n{code}"),
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