"""
backend/utils/llm.py
Primary:  Google Gemini (native google-genai SDK)
Fallback: OpenRouter free models (via httpx)
"""

import asyncio
import json
import os
import re

import httpx

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

OPENROUTER_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-2-9b-it:free",
]


def get_client():
    global _client
    if _client is None and _GENAI_AVAILABLE:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key and api_key != "your_gemini_api_key_here":
            _client = _genai.Client(api_key=api_key)
    return _client


async def _generate_openrouter(prompt: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    # BUG WAS HERE: `if not api_key or api_key` is always True — fixed below
    if not api_key or api_key == "your_openrouter_key_here":
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
        "max_tokens": 800,
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


async def generate(prompt: str, retries: int = 3) -> str:
    gemini_client = get_client()

    if gemini_client is not None:
        for model in GEMINI_MODELS:
            for attempt in range(retries):
                try:
                    response = gemini_client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config={"max_output_tokens": 800, "temperature": 0.1},
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
                        break
        print("[Gemini] All models exhausted — falling back to OpenRouter")

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key and openrouter_key != "your_openrouter_key_here":
        try:
            result = await _generate_openrouter(prompt)
            print(f"[OpenRouter] Success with {os.getenv('OPENROUTER_MODEL', OPENROUTER_MODELS[0])}")
            return result
        except Exception as e:
            print(f"[OpenRouter] Failed: {e}")

    raise RuntimeError(
        "All LLM providers failed.\n"
        "  • Set DEMO_MODE=true for instant mock data\n"
        "  • Or set OPENROUTER_API_KEY in .env (free at openrouter.ai)"
    )


def extract_json(raw: str) -> str:
    """
    Robustly extract a JSON object from LLM response.
    Handles: markdown fences, truncated JSON, trailing commas, extra text.
    """
    if not raw:
        return "{}"

    raw = raw.strip()

    # Strip markdown fences — try all parts between ```
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break

    # Find outermost { ... } by walking the string character by character
    start = raw.find("{")
    if start == -1:
        return "{}"

    depth = 0
    end = -1
    in_string = False
    escape_next = False

    for i, ch in enumerate(raw[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end == -1:
        # Truncated — attempt repair
        return _repair_json(raw[start:])

    return raw[start:end]


def _repair_json(broken: str) -> str:
    """Best-effort repair of truncated JSON from LLM."""
    # Remove trailing commas before closing braces/brackets
    broken = re.sub(r",\s*([}\]])", r"\1", broken)

    # Strip trailing incomplete token (ends mid-key or mid-value)
    broken = broken.rstrip()
    if broken and broken[-1] not in ('"', "}", "]") and not broken[-1].isdigit():
        last_safe = max(broken.rfind(","), broken.rfind("{"), broken.rfind("["))
        if last_safe > 0:
            broken = broken[:last_safe]

    # Remove any dangling trailing comma
    broken = re.sub(r",\s*$", "", broken.rstrip())

    # Close unclosed arrays and objects
    broken += "]" * (broken.count("[") - broken.count("]"))
    broken += "}" * (broken.count("{") - broken.count("}"))

    try:
        json.loads(broken)
        return broken
    except Exception:
        return "{}"


def safe_parse(raw: str, agent_name: str) -> dict:
    """
    Full pipeline: extract JSON → parse → return dict.
    NEVER raises. Always returns a valid dict agents can use.
    """
    fallback = {
        "agent_name": agent_name,
        "issues": [],
        "summary": f"{agent_name} could not parse LLM response. Review manually.",
        "score": 50,
    }
    try:
        extracted = extract_json(raw)
        if not extracted or extracted == "{}":
            print(f"[{agent_name}] extract_json returned empty. Raw[:200]: {raw[:200]}")
            return fallback
        parsed = json.loads(extracted)
        if not isinstance(parsed, dict):
            return fallback
        parsed.setdefault("agent_name", agent_name)
        parsed.setdefault("issues", [])
        parsed.setdefault("summary", "No summary provided.")
        parsed.setdefault("score", 50)
        return parsed
    except Exception as e:
        print(f"[{agent_name}] safe_parse error: {e} | Raw[:300]: {raw[:300]}")
        return fallback