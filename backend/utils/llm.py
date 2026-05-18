"""
backend/utils/llm.py — LLM provider for CodeSentinel

Primary:  Google Gemini (native google-genai SDK, your original code)
Fallback: OpenRouter free models (via httpx, no LangChain needed)

Your agents call: await generate(prompt)  ← unchanged
"""

import asyncio
import json
import os

import httpx

# ── Gemini setup ──────────────────────────────────────────────────────────────

try:
    from google import genai as _genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

_client = None

GEMINI_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]


def get_client():
    global _client
    if _client is None and _GENAI_AVAILABLE:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key and api_key != "your_gemini_api_key_here":
            _client = _genai.Client(api_key=api_key)
    return _client


# ── OpenRouter fallback ───────────────────────────────────────────────────────

OPENROUTER_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-2-9b-it:free",
]


async def _generate_openrouter(prompt: str) -> str:
    """Call OpenRouter API directly via httpx — no LangChain needed."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    model = os.getenv("OPENROUTER_MODEL", OPENROUTER_MODELS[0])

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/codesentinel",
        "X-Title": "CodeSentinel",
    }

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": 0.1,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


# ── Main generate() — called by all agents ───────────────────────────────────

async def generate(prompt: str, retries: int = 3) -> str:
    """
    Generate a response. Tries Gemini first, falls back to OpenRouter.
    Interface is identical to your original — agents don't need any changes.
    """
    gemini_client = get_client()

    # ── Path A: Gemini ────────────────────────────────────────────────────────
    if gemini_client is not None:
        for model in GEMINI_MODELS:
            for attempt in range(retries):
                try:
                    response = gemini_client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config={"max_output_tokens": 600, "temperature": 0.1},
                    )
                    return response.text.strip()
                except Exception as e:
                    err = str(e)
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        wait = (attempt + 1) * 15
                        print(f"[Gemini/{model}] 429 — waiting {wait}s (attempt {attempt+1}/{retries})")
                        await asyncio.sleep(wait)
                    else:
                        print(f"[Gemini/{model}] Error: {e} — trying next model")
                        break  # try next Gemini model immediately

        print("[Gemini] All models exhausted — falling back to OpenRouter")

    # ── Path B: OpenRouter ────────────────────────────────────────────────────
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key and openrouter_key != "your_openrouter_key_here":
        try:
            result = await _generate_openrouter(prompt)
            print(f"[OpenRouter] Success with {os.getenv('OPENROUTER_MODEL', OPENROUTER_MODELS[0])}")
            return result
        except Exception as e:
            print(f"[OpenRouter] Failed: {e}")

    # ── Both failed ───────────────────────────────────────────────────────────
    raise RuntimeError(
        "All LLM providers failed.\n"
        "  • Gemini quota: https://aistudio.google.com\n"
        "  • OpenRouter:   set OPENROUTER_API_KEY in .env\n"
        "  • Quick demo:   set DEMO_MODE=true in .env"
    )


# ── Utility — used by agents to parse Gemini/OpenRouter JSON responses ────────

def extract_json(raw: str) -> str:
    """
    Extract JSON object from LLM response, stripping markdown fences.
    Identical to your original — no changes needed in agents.
    """
    raw = raw.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    start = raw.find("{")
    end = raw.rfind("}") + 1
    return raw[start:end]