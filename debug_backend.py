"""
debug_response.py
Run this 3 times in a row against the LIVE Render backend to check
if agent results get mixed up across runs (backend bug) or stay
correct (meaning the bug is in the frontend).

Usage:
    python debug_response.py
"""
import json
import requests

BASE_URL = "https://codesentinel-backend-cqfi.onrender.com"

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
    f"{BASE_URL}/review",
    json={"code": CODE},
    timeout=180,
)

print(f"Status: {resp.status_code}")
data = resp.json()

print("\n=== ISSUES PER AGENT (agent_name field vs dict key) ===")
for agent_key in ["security", "performance", "logic", "style"]:
    agent_data = data.get(agent_key, {})
    issues = agent_data.get("issues", [])
    print(f"\nDICT KEY: {agent_key}")
    print(f"  agent_name field: {agent_data.get('agent_name')}")
    print(f"  score: {agent_data.get('score')}")
    print(f"  issues count: {len(issues)}")
    if issues:
        # Print first issue description to fingerprint which agent's content this is
        print(f"  first issue desc: {issues[0].get('description', '')[:80]}")