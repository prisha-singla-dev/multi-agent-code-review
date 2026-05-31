"""
trigger_review.py
Run this from your project root to manually trigger a real PR review.
It calls /webhook/trigger which runs the full agent pipeline and posts
a comment on your actual GitHub PR.

Usage:
    python trigger_review.py

Make sure your FastAPI server is running:
    uvicorn backend.main:app --reload --port 8000
"""

import requests
# ── EDIT THESE 3 VALUES ───────────────────────────────────────────────────────
OWNER     = "prisha-singla-dev"               # your GitHub username
REPO      = "multi-agent-code-review"  # your repo name (exact, case-sensitive)
PR_NUMBER = 1                                # the PR number (check the URL: /pull/1)
# ─────────────────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"

def trigger():
    payload = {
        "owner":     OWNER,
        "repo":      REPO,
        "pr_number": PR_NUMBER,
        "title":     "test: add intentionally buggy code for CodeSentinel demo",
    }

    print(f"Triggering review for: {OWNER}/{REPO} PR #{PR_NUMBER}")
    print(f"Calling: {BASE_URL}/webhook/trigger\n")

    resp = requests.post(
        f"{BASE_URL}/webhook/trigger",
        json=payload,
        timeout=10,
    )

    print(f"Status: {resp.status_code}")
    data = resp.json()
    for k, v in data.items():
        print(f"  {k}: {v}")

    print()
    if data.get("will_post_github_comment"):
        print(" Review is running in background.")
        print("   Watch your FastAPI server terminal for agent logs.")
        print(f"   Then check: https://github.com/{OWNER}/{REPO}/pull/{PR_NUMBER}")
    else:
        print("  will_post_github_comment = False")
        print("   Possible causes:")
        print("   1. DEMO_MODE=true in .env  → set DEMO_MODE=false")
        print("   2. owner/repo matched fake list  → check _is_real_repo()")

if __name__ == "__main__":
    trigger()