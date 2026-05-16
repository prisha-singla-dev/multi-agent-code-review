import asyncio
import os
from google import genai

_client: genai.Client | None = None

MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


async def generate(prompt: str, retries: int = 3) -> str:
    client = get_client()
    for model in MODELS:
        for attempt in range(retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={"max_output_tokens": 600, "temperature": 0.1},
                )
                return response.text.strip()
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = (attempt + 1) * 15
                    print(f"[{model}] 429 — waiting {wait}s")
                    await asyncio.sleep(wait)
                else:
                    print(f"[{model}] Error: {e}")
                    break
    raise RuntimeError("All Gemini models exhausted. Check quota at https://aistudio.google.com")

def extract_json(raw: str) -> str:
    """Extract JSON object from Gemini response, stripping markdown fences."""
    raw = raw.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    start = raw.find("{")
    end = raw.rfind("}") + 1
    return raw[start:end]