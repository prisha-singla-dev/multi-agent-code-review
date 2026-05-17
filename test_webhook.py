"""
test_webhook.py — Local webhook test (no real GitHub PR needed)
Run from project ROOT (not backend/):
    python test_webhook.py

FastAPI must be running:
    uvicorn backend.main:app --reload --port 8000
"""
import os
import hashlib
import hmac
import json
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import requests
except ImportError:
    print("requests not installed. Run: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8000"

# Must match GITHUB_WEBHOOK_SECRET in your .env
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "your_webhook_secret_here")


def sign(payload_bytes: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def test_health():
    resp = requests.get(f"{BASE_URL}/health")
    print(f"HEALTH  → {resp.status_code} {resp.json()}")


def test_ping():
    payload = {"zen": "Keep it logically awesome.", "hook_id": 12345}
    body = json.dumps(payload).encode()
    resp = requests.post(
        f"{BASE_URL}/webhook/github",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": sign(body, WEBHOOK_SECRET),
        },
    )
    print(f"PING    → {resp.status_code} {resp.json()}")


def test_pr_opened():
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "title": "Add login feature",
            "html_url": "https://github.com/demo/repo/pull/42",
        },
        "repository": {
            "name": "repo",
            "owner": {"login": "demo"},
        },
    }
    body = json.dumps(payload).encode()
    resp = requests.post(
        f"{BASE_URL}/webhook/github",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sign(body, WEBHOOK_SECRET),
        },
    )
    print(f"PR OPEN → {resp.status_code} {resp.json()}")


def test_manual_trigger():
    resp = requests.post(
        f"{BASE_URL}/webhook/trigger",
        json={"owner": "demo", "repo": "my-repo", "pr_number": 7},
    )
    print(f"TRIGGER → {resp.status_code} {resp.json()}")


def test_bad_signature():
    payload = {"action": "opened"}
    body = json.dumps(payload).encode()
    resp = requests.post(
        f"{BASE_URL}/webhook/github",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalidsignature",
        },
    )
    print(f"BAD SIG → {resp.status_code} {resp.json()} (expected 401)")


if __name__ == "__main__":
    print("=" * 55)
    print("  CodeSentinel — Webhook Test Suite")
    print("=" * 55)
    test_health()
    test_ping()
    test_pr_opened()
    test_manual_trigger()
    test_bad_signature()
    print()
    print("All tests sent. Check server terminal for background task logs.")
    print("In DEMO_MODE, no real GitHub comment is posted.")