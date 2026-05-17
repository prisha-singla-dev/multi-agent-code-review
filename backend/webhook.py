"""
webhook.py — GitHub Webhook receiver for CodeSentinel
Place this file at: backend/webhook.py
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


# ── HMAC verification ────────────────────────────────────────────────────────

def verify_signature(payload_bytes: bytes, signature_header: str | None) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature check.")
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

_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _auth_headers() -> dict:
    h = dict(_HEADERS)
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


async def fetch_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_auth_headers(), params={"per_page": 100})
        resp.raise_for_status()
        return resp.json()


async def fetch_pr_diff(owner: str, repo: str, pr_number: int) -> str:
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
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=_auth_headers(), json={"body": body})
        resp.raise_for_status()
        return resp.json()


# ── Review orchestration ──────────────────────────────────────────────────────

def _build_code_from_files(files: list[dict]) -> str:
    parts: list[str] = []
    for f in files:
        filename = f.get("filename", "unknown")
        patch = f.get("patch", "")
        if patch:
            parts.append(f"### {filename}\n```\n{patch}\n```")
    combined = "\n\n".join(parts)
    return combined[:8_000]


async def run_review_and_comment(payload: dict) -> None:
    pr = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    owner = repo_data.get("owner", {}).get("login", "")
    repo = repo_data.get("name", "")
    pr_number = pr.get("number", 0)
    pr_title = pr.get("title", "Untitled PR")
    pr_url = pr.get("html_url", "")

    logger.info("Starting review for PR #%d — %s/%s", pr_number, owner, repo)

    try:
        if DEMO_MODE:
            from backend.utils.mock_review import get_mock_review
            review_result = get_mock_review()
        else:
            files = await fetch_pr_files(owner, repo, pr_number)
            code_snippet = _build_code_from_files(files)
            if not code_snippet.strip():
                code_snippet = await fetch_pr_diff(owner, repo, pr_number)
                code_snippet = code_snippet[:8_000]

            from backend.orchestrator.graph import run_review
            review_result = await run_review(code_snippet)

        comment_body = _format_github_comment(review_result, pr_title, pr_url)
        result = await post_pr_comment(owner, repo, pr_number, comment_body)
        logger.info("Comment posted: %s", result.get("html_url"))

    except Exception as exc:
        logger.exception("Review failed for PR #%d: %s", pr_number, exc)
        try:
            await post_pr_comment(
                owner, repo, pr_number,
                f"⚠️ **CodeSentinel** encountered an error during review:\n```\n{exc}\n```"
            )
        except Exception:
            pass


def _severity_emoji(severity: str) -> str:
    return {
        "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"
    }.get(severity.lower(), "⚪")


def _format_github_comment(review: Any, pr_title: str, pr_url: str) -> str:
    lines: list[str] = [
        "## 🤖 CodeSentinel — Automated Code Review",
        f"**PR:** [{pr_title}]({pr_url})",
        "",
        "---",
        "",
    ]

    if isinstance(review, dict):
        agents_output = review.get("agents_output", review)
        final_summary = review.get("final_summary", "")
        overall_score = review.get("overall_score", None)
    else:
        agents_output = getattr(review, "agents_output", {})
        final_summary = getattr(review, "final_summary", "")
        overall_score = getattr(review, "overall_score", None)

    agent_icons = {
        "security": "🔒 Security",
        "performance": "⚡ Performance",
        "logic": "🧠 Logic",
        "style": "✨ Style",
    }

    for agent_key, label in agent_icons.items():
        agent_data = agents_output.get(agent_key, {}) if isinstance(agents_output, dict) else {}
        if not agent_data:
            continue

        lines.append(f"### {label} Agent")
        issues = agent_data.get("issues", [])
        if issues:
            for issue in issues:
                sev = issue.get("severity", "info")
                emoji = _severity_emoji(sev)
                title = issue.get("title", issue.get("description", "Issue"))
                desc = issue.get("description", "")
                suggestion = issue.get("suggestion", issue.get("fix", ""))
                lines.append(f"- {emoji} **[{sev.upper()}]** {title}")
                if desc and desc != title:
                    lines.append(f"  > {desc}")
                if suggestion:
                    lines.append(f"  > *{suggestion}*")
        else:
            summary = agent_data.get("summary", agent_data.get("feedback", "No issues found."))
            lines.append(f" {summary}")

        lines.append("")

    lines += ["---", "### Final Recommendation", ""]
    if final_summary:
        lines.append(final_summary)
    else:
        lines.append("Review complete. Please address any flagged issues before merging.")

    if overall_score is not None:
        lines.append(f"\n**Overall Score:** `{overall_score}/10`")

    lines += [
        "",
        "---",
        "*Generated by [CodeSentinel](https://github.com) — Multi-Agent AI Code Review*",
    ]

    return "\n".join(lines)

@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
):
    payload_bytes = await request.body()

    if not verify_signature(payload_bytes, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = x_github_event or "unknown"
    action = payload.get("action", "")

    logger.info("Received GitHub event: %s / action: %s", event, action)

    if event == "pull_request" and action in ("opened", "synchronize", "reopened"):
        background_tasks.add_task(run_review_and_comment, payload)
        pr_num = payload.get("pull_request", {}).get("number")
        return {"status": "accepted", "message": f"Review queued for PR #{pr_num}"}

    if event == "ping":
        return {"status": "pong", "message": "Webhook connected successfully"}

    return {"status": "ignored", "event": event, "action": action}


@router.post("/webhook/trigger")
async def manual_trigger(request: Request, background_tasks: BackgroundTasks):
    """Manually trigger a review without a real GitHub PR — for local testing."""
    body = await request.json()
    owner = body.get("owner", "demo")
    repo = body.get("repo", "demo-repo")
    pr_number = body.get("pr_number", 1)

    fake_payload = {
        "action": "opened",
        "pull_request": {
            "number": pr_number,
            "title": f"Manual test PR #{pr_number}",
            "html_url": f"https://github.com/{owner}/{repo}/pull/{pr_number}",
        },
        "repository": {
            "name": repo,
            "owner": {"login": owner},
        },
    }

    background_tasks.add_task(run_review_and_comment, fake_payload)
    return {"status": "triggered", "pr_number": pr_number, "owner": owner, "repo": repo}