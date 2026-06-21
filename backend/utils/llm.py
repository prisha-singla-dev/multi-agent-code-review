"""
backend/utils/llm.py
Primary:  Google Gemini (native google-genai SDK)
Fallback: OpenRouter free models (via httpx) — tries multiple models in order
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
    "gemini-2.0-flash",
]

# Order: coding-tuned model first, then strong general models, then small fast ones.
OPENROUTER_MODELS = [
    "qwen/qwen3-coder:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]


def get_client():
    global _client
    if _client is None and _GENAI_AVAILABLE:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key and api_key != "your_gemini_api_key_here":
            _client = _genai.Client(api_key=api_key)
    return _client


async def _generate_openrouter(prompt: str) -> str:
    """
    Tries each OpenRouter free model in order until one succeeds.
    Handles per-model overload/rate-limit by moving to the next model
    immediately rather than retrying the same one.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or api_key == "your_openrouter_key_here":
        raise RuntimeError("OPENROUTER_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/codesentinel",
        "X-Title": "CodeSentinel",
    }

    # Allow override via env var for a single specific model, else try the list
    forced_model = os.getenv("OPENROUTER_MODEL", "").strip()
    models_to_try = [forced_model] if forced_model else OPENROUTER_MODELS

    last_error = None
    async with httpx.AsyncClient(timeout=60) as client:
        for model in models_to_try:
            try:
                body = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4000,
                    "temperature": 0.1,
                }
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=body,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    if content:
                        print(f"[OpenRouter/{model}] Success")
                        return content
                    print(f"[OpenRouter/{model}] Empty response — trying next model")
                    continue
                else:
                    print(f"[OpenRouter/{model}] HTTP {resp.status_code}: {resp.text[:200]} — trying next model")
                    last_error = f"HTTP {resp.status_code}"
                    continue
            except Exception as e:
                print(f"[OpenRouter/{model}] Error: {e} — trying next model")
                last_error = str(e)
                continue

    raise RuntimeError(f"All OpenRouter models failed. Last error: {last_error}")


async def generate(prompt: str, retries: int = 1, json_mode: bool = True) -> str:
    gemini_client = get_client()
    gemini_failed = False

    if gemini_client is not None:
        for model in GEMINI_MODELS:
            for attempt in range(retries):
                try:
                    config_kwargs = {
                        "max_output_tokens": 4000,
                        "temperature": 0.1,
                    }
                    if json_mode:
                        config_kwargs["response_mime_type"] = "application/json"

                    try:
                        config = _genai_types.GenerateContentConfig(**config_kwargs)
                    except Exception:
                        config = config_kwargs

                    response = gemini_client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config,
                    )
                    text = response.text.strip() if response.text else ""
                    if text:
                        return text
                    print(f"[Gemini/{model}] Empty response - trying next")
                    break
                except Exception as e:
                    err = str(e)
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        wait = 5
                        print(f"[Gemini/{model}] 429 - waiting {wait}s")
                        await asyncio.sleep(wait)
                    else:
                        print(f"[Gemini/{model}] Error: {e}")
                        break
        gemini_failed = True
        print("[Gemini] Exhausted - falling back to OpenRouter")

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    has_openrouter = bool(openrouter_key and openrouter_key != "your_openrouter_key_here")

    if not has_openrouter and gemini_failed:
        print("[CRITICAL] Gemini failed AND OPENROUTER_API_KEY not set on this environment!")

    if has_openrouter:
        try:
            result = await _generate_openrouter(prompt)
            return result
        except Exception as e:
            print(f"[OpenRouter] All models failed: {e}")

    raise RuntimeError(
        "All LLM providers failed.\n"
        "  • Set DEMO_MODE=true for instant mock data\n"
        "  • Or check OPENROUTER_API_KEY in .env"
    )


def extract_json(raw: str) -> str:
    if not raw:
        return "{}"

    raw = raw.strip()

    if "```" in raw:
        raw = re.sub(r"```(?:json|python|javascript)?\s*", "", raw)
        raw = re.sub(r"```", "", raw)
        raw = raw.strip()

    if raw.startswith("{"):
        try:
            json.loads(raw)
            return raw
        except json.JSONDecodeError:
            pass

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
        return _repair_json(raw[start:])

    candidate = raw[start:end]
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        return _repair_json(candidate)


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
    fallback = {
        "agent_name": agent_name,
        "issues": [],
        "summary": f"{agent_name}: could not parse LLM response.",
        "score": 50,
    }
    try:
        extracted = extract_json(raw)
        if not extracted or extracted == "{}":
            print(f"[{agent_name}] extract_json empty.\nFull raw ({len(raw)} chars):\n{raw}\n---")
            return fallback
        parsed = json.loads(extracted)
        if not isinstance(parsed, dict):
            return fallback
        parsed.setdefault("agent_name", agent_name)
        parsed.setdefault("issues", [])
        parsed.setdefault("summary", "No summary provided.")
        parsed.setdefault("score", 50)
        if not isinstance(parsed["issues"], list):
            parsed["issues"] = []
        return parsed
    except Exception as e:
        print(f"[{agent_name}] safe_parse error: {e}\nFull raw ({len(raw)} chars):\n{raw}\n---")
        return fallback