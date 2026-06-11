"""
debug_response.py
Run this to see the EXACT JSON the backend returns.
Paste your bad code inline so we can see the full response shape.

Usage:
    python debug_response.py

Server must be running: uvicorn backend.main:app --reload --port 8000
"""
import json
import requests

# Small sample of bad code — enough to trigger all agents
CODE = '''
import os, subprocess
API_KEY = "sk-prod-abc123"
DB_PASS = "admin123"

def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = subprocess.run(f"echo {user_id}", shell=True)
    return result

def find_dupes(items):
    dupes = []
    for i in range(len(items)):
        for j in range(len(items)):
            if i != j and items[i] == items[j]:
                dupes.append(items[i])
    return dupes

def divide(a, b):
    return a / b

def x(a,b,c):
    z=a+b
    return z*c
'''

resp = requests.post(
    "http://localhost:8000/review",
    json={"code": CODE},
    timeout=300,
)

print(f"Status: {resp.status_code}")
data = resp.json()

print("\n=== FULL RESPONSE STRUCTURE ===")
print(json.dumps(data, indent=2, default=str))

print("\n=== ISSUES PER AGENT ===")
for agent in ["security", "performance", "logic", "style"]:
    agent_data = data.get(agent, {})
    issues = agent_data.get("issues", [])
    print(f"\n{agent.upper()}:")
    print(f"  score: {agent_data.get('score')}")
    print(f"  issues count: {len(issues)}")
    print(f"  issues type: {type(issues)}")
    if issues:
        print(f"  first issue keys: {list(issues[0].keys()) if issues else 'N/A'}")
        print(f"  first issue: {issues[0]}")
    else:
        print(f"  raw issues value: {repr(issues)}")