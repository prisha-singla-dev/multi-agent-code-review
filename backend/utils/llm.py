# """
# backend/utils/llm.py
# Primary:  Google Gemini (native google-genai SDK)
# Fallback: OpenRouter free models (via httpx)
# """
# import asyncio
# import json
# import os
# import re
# import httpx

# try:
#     from google import genai as _genai
#     _GENAI_AVAILABLE = True
# except ImportError:
#     _GENAI_AVAILABLE = False

# _client = None

# GEMINI_MODELS = [
#     "gemini-2.0-flash-lite",
#     "gemini-2.0-flash",
#     "gemini-2.5-flash-lite",
#     "gemini-2.5-flash",
# ]

# OPENROUTER_MODELS = [
#     "meta-llama/llama-3.1-8b-instruct:free",
#     "mistralai/mistral-7b-instruct:free",
#     "google/gemma-2-9b-it:free",
# ]


# def get_client():
#     global _client
#     if _client is None and _GENAI_AVAILABLE:
#         api_key = os.getenv("GEMINI_API_KEY", "")
#         if api_key and api_key != "your_gemini_api_key_here":
#             _client = _genai.Client(api_key=api_key)
#     return _client


# async def _generate_openrouter(prompt: str) -> str:
#     api_key = os.getenv("OPENROUTER_API_KEY", "")
#     if not api_key or api_key == "your_openrouter_key_here":
#         raise RuntimeError("OPENROUTER_API_KEY not set")
#     model = os.getenv("OPENROUTER_MODEL", OPENROUTER_MODELS[0])
#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type": "application/json",
#         "HTTP-Referer": "https://github.com/codesentinel",
#         "X-Title": "CodeSentinel",
#     }
#     body = {
#         "model": model,
#         "messages": [{"role": "user", "content": prompt}],
#         "max_tokens": 800,
#         "temperature": 0.1,
#     }
#     async with httpx.AsyncClient(timeout=60) as client:
#         resp = await client.post(
#             "https://openrouter.ai/api/v1/chat/completions",
#             headers=headers,
#             json=body,
#         )
#         resp.raise_for_status()
#         data = resp.json()
#         return data["choices"][0]["message"]["content"].strip()


# async def generate(prompt: str, retries: int = 3) -> str:
#     gemini_client = get_client()

#     if gemini_client is not None:
#         for model in GEMINI_MODELS:
#             for attempt in range(retries):
#                 try:
#                     response = gemini_client.models.generate_content(
#                         model=model,
#                         contents=prompt,
#                         config={"max_output_tokens": 800, "temperature": 0.1},
#                     )
#                     return response.text.strip()
#                 except Exception as e:
#                     err = str(e)
#                     if "429" in err or "RESOURCE_EXHAUSTED" in err:
#                         wait = (attempt + 1) * 15
#                         print(f"[Gemini/{model}] 429 — waiting {wait}s (attempt {attempt+1}/{retries})")
#                         await asyncio.sleep(wait)
#                     else:
#                         print(f"[Gemini/{model}] Error: {e} — trying next model")
#                         break
#         print("[Gemini] All models exhausted — falling back to OpenRouter")

#     openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
#     if openrouter_key and openrouter_key != "your_openrouter_key_here":
#         try:
#             result = await _generate_openrouter(prompt)
#             print(f"[OpenRouter] Success with {os.getenv('OPENROUTER_MODEL', OPENROUTER_MODELS[0])}")
#             return result
#         except Exception as e:
#             print(f"[OpenRouter] Failed: {e}")

#     raise RuntimeError(
#         "All LLM providers failed.\n"
#         "  • Set DEMO_MODE=true for instant mock data\n"
#         "  • Or set OPENROUTER_API_KEY in .env (free at openrouter.ai)"
#     )


# def extract_json(raw: str) -> str:
#     """
#     Robustly extract a JSON object from LLM response.
#     Handles ALL of these formats Gemini returns:
#       - Raw JSON: {"agent_name": ...}
#       - Fenced:   ```json\n{"agent_name": ...}\n```
#       - Fenced:   ```\n{"agent_name": ...}\n```
#       - Truncated JSON (repaired automatically)
#       - JSON with extra text before/after
#     """
#     if not raw:
#         return "{}"

#     raw = raw.strip()

#     # ── Step 1: Strip markdown fences ────────────────────────────────────────
#     if "```" in raw:
#         # Remove opening fence (```json or ```)
#         raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
#         # Remove closing fence
#         raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
#         raw = raw.strip()

#     # ── Step 2: Find the outermost { ... } by depth-walking ──────────────────
#     start = raw.find("{")
#     if start == -1:
#         return "{}"

#     depth = 0
#     end = -1
#     in_string = False
#     escape_next = False

#     for i, ch in enumerate(raw[start:], start):
#         if escape_next:
#             escape_next = False
#             continue
#         if ch == "\\" and in_string:
#             escape_next = True
#             continue
#         if ch == '"':
#             in_string = not in_string
#             continue
#         if in_string:
#             continue
#         if ch == "{":
#             depth += 1
#         elif ch == "}":
#             depth -= 1
#             if depth == 0:
#                 end = i + 1
#                 break

#     if end == -1:
#         # Truncated response — attempt repair
#         return _repair_json(raw[start:])

#     candidate = raw[start:end]

#     # ── Step 3: Validate — if it parses cleanly, return it ───────────────────
#     try:
#         json.loads(candidate)
#         return candidate
#     except json.JSONDecodeError:
#         return _repair_json(candidate)


# def _repair_json(broken: str) -> str:
#     """
#     Best-effort repair of truncated or malformed JSON from LLM.
#     Handles: trailing commas, unclosed arrays/objects, mid-token truncation.
#     """
#     if not broken:
#         return "{}"

#     # Remove trailing commas before closing tokens
#     broken = re.sub(r",\s*([}\]])", r"\1", broken)

#     # Strip trailing incomplete token (ends mid-string or mid-key)
#     broken = broken.rstrip()
#     if broken and broken[-1] not in ('"', "}", "]") and not broken[-1].isdigit():
#         # Cut back to the last safe boundary
#         last_safe = max(broken.rfind(","), broken.rfind("{"), broken.rfind("["))
#         if last_safe > 0:
#             broken = broken[:last_safe]

#     # Remove any trailing comma left behind
#     broken = re.sub(r",\s*$", "", broken.rstrip())

#     # Close unclosed arrays then objects (order matters)
#     open_brackets = broken.count("[") - broken.count("]")
#     open_braces = broken.count("{") - broken.count("}")
#     broken += "]" * max(open_brackets, 0)
#     broken += "}" * max(open_braces, 0)

#     try:
#         json.loads(broken)
#         return broken
#     except Exception:
#         return "{}"


# def safe_parse(raw: str, agent_name: str) -> dict:
#     """
#     Full pipeline: strip fences → extract JSON → parse → return dict.
#     NEVER raises. Always returns a usable dict with all required keys set.
#     """
#     fallback = {
#         "agent_name": agent_name,
#         "issues": [],
#         "summary": f"{agent_name}: could not parse LLM response — review manually.",
#         "score": 50,
#     }
#     try:
#         extracted = extract_json(raw)
#         if not extracted or extracted == "{}":
#             print(f"[{agent_name}] extract_json returned empty. Raw[:300]:\n{raw[:300]}")
#             return fallback
#         parsed = json.loads(extracted)
#         if not isinstance(parsed, dict):
#             return fallback
#         # Ensure all required keys exist
#         parsed.setdefault("agent_name", agent_name)
#         parsed.setdefault("issues", [])
#         parsed.setdefault("summary", "No summary provided.")
#         parsed.setdefault("score", 50)
#         return parsed
#     except Exception as e:
#         print(f"[{agent_name}] safe_parse error: {e}\nRaw[:300]:\n{raw[:300]}")
#         return fallback

"""
backend/utils/llm.py
Primary:  Google Gemini (native google-genai SDK)
Fallback: OpenRouter free models (via httpx)

Speed strategy:
- Try gemini-2.5-flash first (highest quota, been succeeding)
- On 429: immediately try next model, NO waiting
- Only wait if ALL models are exhausted once, then one short retry pass
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

# gemini-2.5-flash has highest free quota — try it first
# gemini-2.0-flash-lite has lowest quota — try it last
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


async def generate(prompt: str) -> str:
    """
    Fast model selection strategy:
    Pass 1 — try every model ONCE with zero waiting on 429.
              First model that responds → return immediately.
    Pass 2 — if all 429'd, wait 20s once, then try all again.
    Pass 3 — try OpenRouter.
    """
    gemini_client = get_client()

    if gemini_client is not None:
        # ── Pass 1: try each model once, skip immediately on 429 ─────────────
        for model in GEMINI_MODELS:
            try:
                response = gemini_client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={"max_output_tokens": 2048, "temperature": 0.1},
                )
                print(f"[Gemini/{model}] ✓ success")
                return response.text.strip()
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    print(f"[Gemini/{model}] 429 — skipping to next model")
                    continue  # immediately try next model, no sleep
                else:
                    print(f"[Gemini/{model}] Error: {e} — skipping")
                    continue

        # ── Pass 2: all models hit 429 — wait once, then retry all ───────────
        print("[Gemini] All models rate-limited. Waiting 20s then retrying...")
        await asyncio.sleep(20)

        for model in GEMINI_MODELS:
            try:
                response = gemini_client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={"max_output_tokens": 2048, "temperature": 0.1},
                )
                print(f"[Gemini/{model}] ✓ success (pass 2)")
                return response.text.strip()
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    print(f"[Gemini/{model}] 429 again — skipping")
                    continue
                else:
                    print(f"[Gemini/{model}] Error: {e} — skipping")
                    continue

        print("[Gemini] Pass 2 exhausted — falling back to OpenRouter")

    # ── Pass 3: OpenRouter ────────────────────────────────────────────────────
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key and openrouter_key != "your_openrouter_key_here":
        try:
            result = await _generate_openrouter(prompt)
            print(f"[OpenRouter] ✓ success")
            return result
        except Exception as e:
            print(f"[OpenRouter] Failed: {e}")

    raise RuntimeError(
        "All LLM providers failed.\n"
        "  • Set DEMO_MODE=true for instant mock data\n"
        "  • Or set OPENROUTER_API_KEY in .env (free at openrouter.ai)"
    )


def extract_json(raw: str) -> str:
    if not raw:
        return "{}"
    raw = raw.strip()
    if "```" in raw:
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
        raw = raw.strip()
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
        "summary": f"{agent_name}: could not parse LLM response — review manually.",
        "score": 50,
    }
    try:
        extracted = extract_json(raw)
        if not extracted or extracted == "{}":
            print(f"[{agent_name}] extract_json returned empty. Raw[:300]:\n{raw[:300]}")
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
        print(f"[{agent_name}] safe_parse error: {e}\nRaw[:300]:\n{raw[:300]}")
        return fallback