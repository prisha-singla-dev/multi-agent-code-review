"""
backend/webhook.py - GitHub Webhook receiver for CodeSentinel
"""

import hashlib
import hmac
import json
import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter()

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"


# ── HMAC verification ─────────────────────────────────────────────────────────

def verify_signature(payload_bytes: bytes, signature_header: str | None) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not set - skipping signature check.")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


# ── GitHub API helpers ────────────────────────────────────────────────────────

GITHUB_API = "https://api.github.com"

_BASE_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _auth_headers() -> dict:
    h = dict(_BASE_HEADERS)
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _is_real_repo(owner: str, repo: str) -> bool:
    """
    Return False only for the specific fake repos used in test_webhook.py.
    Any real GitHub username/repo will pass through.
    """
    FAKE_OWNERS = {"demo", "test", "example"}
    FAKE_REPOS  = {"demo-repo", "my-repo", "repo", "test-repo"}
    return not (owner.lower() in FAKE_OWNERS and repo.lower() in FAKE_REPOS)


async def fetch_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_auth_headers(), params={"per_page": 100})
        resp.raise_for_status()
        return resp.json()


async def fetch_pr_diff_text(owner: str, repo: str, pr_number: int) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            url,
            headers={**_auth_headers(), "Accept": "application/vnd.github.diff"},
        )
        resp.raise_for_status()
        return resp.text


async def post_pr_comment(owner: str, repo: str, pr_number: int, body: str) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=_auth_headers(), json={"body": body})
        resp.raise_for_status()
        return resp.json()


# ── Code extraction ───────────────────────────────────────────────────────────

def _build_code_from_files(files: list[dict]) -> str:
    parts: list[str] = []
    for f in files:
        filename = f.get("filename", "unknown")
        patch = f.get("patch", "")
        if patch:
            parts.append(f"### {filename}\n```\n{patch}\n```")
    return "\n\n".join(parts)[:8_000]


# ── Main review background task ───────────────────────────────────────────────

async def run_review_and_comment(payload: dict) -> None:
    pr        = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    owner     = repo_data.get("owner", {}).get("login", "")
    repo      = repo_data.get("name", "")
    pr_number = pr.get("number", 0)
    pr_title  = pr.get("title", "Untitled PR")
    pr_url    = pr.get("html_url", "")

    is_real = _is_real_repo(owner, repo)

    logger.info(
        "Starting review for PR #%d - %s/%s (real_repo=%s, demo_mode=%s)",
        pr_number, owner, repo, is_real, DEMO_MODE,
    )

    try:
        # ── Decide: mock or real agents ──────────────────────────────────────
        if DEMO_MODE or not is_real:
            from backend.utils.mock_review import get_mock_review
            review_result = get_mock_review()
            logger.info(
                "Using mock review (demo_mode=%s, real_repo=%s)", DEMO_MODE, is_real
            )
        else:
            # Fetch PR diff from GitHub
            code_snippet = ""
            try:
                files = await fetch_pr_files(owner, repo, pr_number)
                code_snippet = _build_code_from_files(files)
                logger.info("Fetched %d changed files", len(files))
            except Exception as e:
                logger.warning("fetch_pr_files failed: %s - falling back to diff", e)

            if not code_snippet.strip():
                code_snippet = await fetch_pr_diff_text(owner, repo, pr_number)
                code_snippet = code_snippet[:8_000]
                logger.info("Fetched PR diff (%d chars)", len(code_snippet))

            from backend.orchestrator.graph import run_review
            review_result = await run_review(code_snippet)
            logger.info("Review complete - posting comment")

        # ── Format and post comment ───────────────────────────────────────────
        comment_body = _format_github_comment(review_result, pr_title, pr_url)

        if not is_real:
            # Test/fake repo - log instead of posting
            logger.info(
                "TEST MODE - comment NOT posted to GitHub. Preview:\n%s",
                comment_body[:600],
            )
            return

        result = await post_pr_comment(owner, repo, pr_number, comment_body)
        logger.info("✅ Comment posted: %s", result.get("html_url", "no URL"))

    except Exception as exc:
        logger.exception("Review pipeline failed for PR #%d: %s", pr_number, exc)
        # Best-effort error comment so the PR author knows something went wrong
        if is_real:
            try:
                await post_pr_comment(
                    owner, repo, pr_number,
                    f"⚠️ **CodeSentinel** encountered an error:\n```\n{exc}\n```\n"
                    f"Please check the server logs.",
                )
            except Exception:
                pass


# ── GitHub comment formatter ──────────────────────────────────────────────────

def _severity_emoji(severity: str) -> str:
    return {
        "critical": "🔴",
        "high":     "🟠",
        "medium":   "🟡",
        "low":      "🟢",
        "info":     "ℹ️",
    }.get(severity.lower(), "⚪")


def _format_github_comment(review: Any, pr_title: str, pr_url: str) -> str:
    lines: list[str] = [
        "## 🤖 CodeSentinel - Automated Code Review",
        f"**PR:** [{pr_title}]({pr_url})",
        "",
        "---",
    ]

    # Support both ReviewResponse objects and plain dicts
    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    agent_configs = [
        ("security",    "🔒 Security Agent"),
        ("performance", "⚡ Performance Agent"),
        ("logic",       "🧠 Logic Agent"),
        ("style",       "✨ Style Agent"),
    ]

    for field, label in agent_configs:
        agent = _get(review, field)
        if agent is None:
            continue

        score   = _get(agent, "score", "N/A")
        summary = _get(agent, "summary", "")
        issues  = _get(agent, "issues", [])

        lines.append(f"\n### {label} - Score: `{score}/100`")
        lines.append(f"> {summary}")

        if issues:
            lines.append("")
            for issue in issues:
                sev        = _get(issue, "severity", "info")
                desc       = _get(issue, "description", "")
                suggestion = _get(issue, "suggestion", "")
                line_ref   = _get(issue, "line", None)

                loc = f" (line {line_ref})" if line_ref and line_ref != "null" else ""
                lines.append(f"- {_severity_emoji(sev)} **[{sev.upper()}]**{loc} {desc}")
                if suggestion:
                    lines.append(f"  - 💡 {suggestion}")
        else:
            lines.append("\n✅ No issues found.")

    # Final recommendation
    final = _get(review, "final_recommendation", "") or _get(review, "final_summary", "")
    overall = _get(review, "overall_score", None)
    total = _get(review, "total_issues", None)

    lines += [
        "",
        "---",
        "### 📋 Final Recommendation",
        "",
        final or "Review complete. Check individual agent findings above.",
    ]

    if overall is not None:
        lines.append(f"\n**Overall Score:** `{overall}/100`")
    if total is not None:
        lines.append(f"**Total Issues:** `{total}`")

    lines += [
        "",
        "---",
        "*🤖 Generated by [CodeSentinel](https://github.com) - Multi-Agent AI Code Review*",
    ]

    return "\n".join(lines)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
):
    """
    Receives GitHub webhook POST events.
    Payload URL must be: https://YOUR-NGROK-URL.ngrok-free.app/webhook/github
    """
    payload_bytes = await request.body()

    if not verify_signature(payload_bytes, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event  = x_github_event or "unknown"
    action = payload.get("action", "")
    logger.info("GitHub event received: %s / action: %s", event, action)

    if event == "pull_request" and action in ("opened", "synchronize", "reopened"):
        background_tasks.add_task(run_review_and_comment, payload)
        pr_num = payload.get("pull_request", {}).get("number")
        return {"status": "accepted", "message": f"Review queued for PR #{pr_num}"}

    if event == "ping":
        return {"status": "pong", "message": "Webhook connected successfully ✅"}

    return {"status": "ignored", "event": event, "action": action}


@router.post("/webhook/trigger")
async def manual_trigger(request: Request, background_tasks: BackgroundTasks):
    """
    Manually trigger a review - for local testing without a real GitHub event.
    Use real owner/repo/pr_number to post an actual GitHub comment.
    Use demo/demo-repo/1 to just log the output without hitting GitHub.
    """
    body      = await request.json()
    owner     = body.get("owner", "demo")
    repo      = body.get("repo", "demo-repo")
    pr_number = body.get("pr_number", 1)

    fake_payload = {
        "action": "opened",
        "pull_request": {
            "number":   pr_number,
            "title":    body.get("title", f"Manual test PR #{pr_number}"),
            "html_url": f"https://github.com/{owner}/{repo}/pull/{pr_number}",
        },
        "repository": {
            "name":  repo,
            "owner": {"login": owner},
        },
    }

    background_tasks.add_task(run_review_and_comment, fake_payload)
    is_real = _is_real_repo(owner, repo)
    return {
        "status":                  "triggered",
        "pr_number":               pr_number,
        "owner":                   owner,
        "repo":                    repo,
        "will_post_github_comment": is_real and not DEMO_MODE,
        "note": (
            "Using mock review (test owner/repo)" if not is_real else
            "Using mock review (DEMO_MODE=true)"  if DEMO_MODE    else
            "Running real agents + posting GitHub comment"
        ),
    }