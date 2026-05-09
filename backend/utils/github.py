import httpx
import os
import re
from typing import Optional


def parse_pr_url(url: str) -> Optional[tuple[str, str, int]]:
    """Parse GitHub PR URL into (owner, repo, pr_number)."""
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if not match:
        return None
    return match.group(1), match.group(2), int(match.group(3))


async def fetch_pr_diff(pr_url: str) -> str:
    """Fetch the diff/files from a GitHub PR."""
    parsed = parse_pr_url(pr_url)
    if not parsed:
        raise ValueError(f"Invalid GitHub PR URL: {pr_url}")

    owner, repo, pr_number = parsed
    token = os.getenv("GITHUB_TOKEN")

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient() as client:
        # Fetch PR files
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files",
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        files = resp.json()

    code_parts = []
    for f in files[:10]:  # limit to 10 files
        filename = f.get("filename", "")
        patch = f.get("patch", "")
        if patch:
            code_parts.append(f"# File: {filename}\n{patch}")

    if not code_parts:
        raise ValueError("No code changes found in this PR.")

    return "\n\n".join(code_parts)