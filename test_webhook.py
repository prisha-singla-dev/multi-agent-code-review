"""
test_webhook.py — Local webhook test suite
Run from project ROOT:
    python test_webhook.py

FastAPI must be running in another terminal:
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
    print("Run: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8000"

# ⚠️  Must match GITHUB_WEBHOOK_SECRET in your .env file exactly
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "your_webhook_secret_here")


def sign(payload_bytes: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def sep(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print('─' * 55)


def test_health():
    sep("1. Health check")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"  → {resp.status_code} {resp.json()}")
    assert resp.status_code == 200, "Server not running!"


def test_ping():
    sep("2. Ping event (GitHub sends this on webhook creation)")
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
    print(f"  → {resp.status_code} {resp.json()}")
    assert resp.status_code == 200


def test_pr_opened_fake():
    sep("3. PR opened (fake repo — no GitHub API call, logs comment to console)")
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "title": "Add login feature",
            "html_url": "https://github.com/demo/repo/pull/42",
        },
        "repository": {
            "name": "repo",            # ← fake repo name, skips GitHub API
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
    print(f"  → {resp.status_code} {resp.json()}")
    print("  ✅ Check server terminal — it will LOG the review comment (not post to GitHub)")
    assert resp.status_code == 200


def test_manual_trigger_fake():
    sep("4. Manual trigger (fake repo — logs to server terminal)")
    resp = requests.post(
        f"{BASE_URL}/webhook/trigger",
        json={"owner": "demo", "repo": "demo-repo", "pr_number": 7},
    )
    print(f"  → {resp.status_code} {resp.json()}")
    assert resp.status_code == 200


def test_bad_signature():
    sep("5. Bad signature (should return 401)")
    payload = {"action": "opened"}
    body = json.dumps(payload).encode()
    resp = requests.post(
        f"{BASE_URL}/webhook/github",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalidsignature000",
        },
    )
    print(f"  → {resp.status_code} {resp.json()} ✅ (401 is correct)")
    assert resp.status_code == 401


def test_ignored_event():
    sep("6. Push event (should be ignored, not reviewed)")
    payload = {"ref": "refs/heads/main"}
    body = json.dumps(payload).encode()
    resp = requests.post(
        f"{BASE_URL}/webhook/github",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": sign(body, WEBHOOK_SECRET),
        },
    )
    print(f"  → {resp.status_code} {resp.json()} ✅ (ignored is correct)")
    assert resp.status_code == 200


if __name__ == "__main__":
    print("=" * 55)
    print("  CodeSentinel — Webhook Test Suite")
    print("=" * 55)
    print(f"  Target: {BASE_URL}")
    print(f"  Secret: {'*' * (len(WEBHOOK_SECRET) - 4) + WEBHOOK_SECRET[-4:]}")

    try:
        test_health()
        test_ping()
        test_pr_opened_fake()
        test_manual_trigger_fake()
        test_bad_signature()
        test_ignored_event()

        print("\n" + "=" * 55)
        print("  ✅ All tests passed!")
        print("=" * 55)
        print("""
Next steps:
  1. Fix GitHub webhook URL → must end with /webhook/github
     Correct:   https://xxxx.ngrok-free.app/webhook/github
     Wrong:     https://xxxx.ngrok-free.app/

  2. In GitHub → repo → Settings → Webhooks → Edit:
     Update Payload URL to: https://xxxx.ngrok-free.app/webhook/github

  3. Open a real PR on your repo to test the full flow
""")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)