import os
from google import genai

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


MODEL = "models/gemini-2.5-flash"


async def generate(prompt: str) -> str:
    """Single async call to Gemini. Returns text content."""
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )
    return response.text.strip()