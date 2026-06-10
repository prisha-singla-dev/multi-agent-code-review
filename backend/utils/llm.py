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
    from google.genai import types as _genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

_client = None

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
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
        "max_tokens": 4000,
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


async def generate(prompt: str, retries: int = 2) -> str:
    gemini_client = get_client()

    if gemini_client is not None:
        for model in GEMINI_MODELS:
            for attempt in range(retries):
                try:
                    try:
                        config = _genai_types.GenerateContentConfig(
                            response_mime_type="application/json",
                            max_output_tokens=4000,
                            temperature=0.1,
                        )
                    except Exception:
                        # Fallback if types module unavailable
                        config = {
                            "max_output_tokens": 4000,
                            "temperature": 0.1,
                        }

                    response = gemini_client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config,
                    )
                    text = response.text.strip() if response.text else ""
                    if text:
                        return text
                    print(f"[Gemini/{model}] Empty response — trying next model")
                    break
                except Exception as e:
                    err = str(e)
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        wait = (attempt + 1) * 10
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
            print(f"[OpenRouter] Success")
            return result
        except Exception as e:
            print(f"[OpenRouter] Failed: {e}")

    raise RuntimeError(
        "All LLM providers failed.\n"
        "  • Set DEMO_MODE=true for instant mock data\n"
        "  • Or set OPENROUTER_API_KEY in .env"
    )


def extract_json(raw: str) -> str:
    """
    Extract JSON from LLM response.
    With response_mime_type=application/json, Gemini returns raw JSON directly.
    This still handles legacy/fallback cases with markdown fences.
    """
    if not raw:
        return "{}"

    raw = raw.strip()

    # Strip markdown fences if present (shouldn't happen with mime_type set)
    if "```" in raw:
        raw = re.sub(r"```(?:json|python|javascript)?\s*", "", raw)
        raw = re.sub(r"```", "", raw)
        raw = raw.strip()

    # If it starts with { directly — common with application/json mode
    if raw.startswith("{"):
        try:
            json.loads(raw)
            return raw  # Already valid JSON
        except json.JSONDecodeError:
            pass  # Fall through to depth walker

    start = raw.find("{")
    if start == -1:
        return "{}"

    # Depth-walk to find true closing brace
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
        return _repair_json(raw[start:])

    candidate = raw[start:end]
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        return _repair_json(candidate)

# fixing json 
def _repair_json(broken: str) -> str:
    if not broken:
        return "{}"
    broken = re.sub(r",\s*([}\]])", r"\1", broken)
    broken = broken.rstrip()
    if broken and broken[-1] not in ('"', "}", "]") and not broken[-1].isdigit():
        last_safe = max(broken.rfind(","), broken.rfind("{"), broken.rfind("["))
        if last_safe > 0:
            broken = broken[:last_safe]
    broken = re.sub(r",\s*$", "", broken.rstrip())
    broken += "]" * max(broken.count("[") - broken.count("]"), 0)
    broken += "}" * max(broken.count("{") - broken.count("}"), 0)
    try:
        json.loads(broken)
        return broken
    except Exception:
        return "{}"


def safe_parse(raw: str, agent_name: str) -> dict:
    """Never raises. Always returns a usable dict."""
    fallback = {
        "agent_name": agent_name,
        "issues": [],
        "summary": f"{agent_name}: could not parse LLM response.",
        "score": 50,
    }
    try:
        extracted = extract_json(raw)
        if not extracted or extracted == "{}":
            # Print full raw for debugging (not truncated)
            print(f"[{agent_name}] extract_json empty.\nFull raw ({len(raw)} chars):\n{raw}\n---")
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
        print(f"[{agent_name}] safe_parse error: {e}\nFull raw ({len(raw)} chars):\n{raw}\n---")
        return fallback