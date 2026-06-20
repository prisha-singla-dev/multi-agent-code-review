"""
trigger_review.py
Run this from your project root to manually trigger a real PR review
against your DEPLOYED Render backend.

Usage:
    python trigger_review.py

No need to run locally or switch branches — this just calls your
live Render API over the internet.
"""

import requests

# ── EDIT THESE VALUES ─────────────────────────────────────────────────────────
OWNER     = "prisha-singla-dev"
REPO      = "multi-agent-code-review"   # exact repo name, case-sensitive
PR_NUMBER = 1
# ─────────────────────────────────────────────────────────────────────────────

# FIX: no trailing slash — was causing // double-slash bug
BASE_URL = "https://codesentinel-backend-cqfi.onrender.com"


def trigger():
    payload = {
        "owner":     OWNER,
        "repo":      REPO,
        "pr_number": PR_NUMBER,
        "title":     "test: add intentionally buggy code for CodeSentinel demo",
    }

    url = f"{BASE_URL}/webhook/trigger"
    print(f"Triggering review for: {OWNER}/{REPO} PR #{PR_NUMBER}")
    print(f"Calling: {url}\n")
    print("Note: Render free tier sleeps after 15min idle.")
    print("First request may take 30-50s to wake up the server.\n")

    resp = requests.post(url, json=payload, timeout=90)

    print(f"Status: {resp.status_code}")
    try:
        data = resp.json()
        for k, v in data.items():
            print(f"  {k}: {v}")
    except Exception:
        print(f"  Raw response: {resp.text[:500]}")
        return

    print()
    if data.get("will_post_github_comment"):
        print("✅ Review is running in background on Render.")
        print(f"   Check: https://github.com/{OWNER}/{REPO}/pull/{PR_NUMBER}")
        print("   May take 1-3 minutes (Gemini calls + Render compute).")
    else:
        print("⚠️  will_post_github_comment = False")
        print("   Check Render logs (dashboard → Logs tab) for details.")


if __name__ == "__main__":
    trigger()