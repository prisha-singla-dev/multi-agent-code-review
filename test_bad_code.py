"""
test_bad_code.py
Intentionally buggy code to trigger all 4 agents.
Commit this to a branch and open a PR to test the full webhook flow.
"""
import os
import subprocess
import json

# ── SECURITY ISSUES ───────────────────────────────────────────────────────────
API_KEY = "sk-prod-abc123secretkey"       # hardcoded secret
DB_PASSWORD = "admin123"                  # hardcoded credential
SECRET_TOKEN = "ghp_realtoken12345"       # hardcoded GitHub token


def get_user(user_id):
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    
    # Shell injection vulnerability  
    result = subprocess.run(f"echo {user_id}", shell=True, capture_output=True)
    return result.stdout


def authenticate(username, password):
    # Hardcoded admin backdoor
    if username == "admin" and password == "admin":
        return True
    return False


# ── PERFORMANCE ISSUES ────────────────────────────────────────────────────────
def get_all_users():
    users = []
    # N+1 query pattern — fetches one user at a time in a loop
    for i in range(1000):
        user = {"id": i, "name": f"user_{i}"}  # simulated DB call per iteration
        users.append(user)
    return users


def find_duplicates(items):
    # O(n²) when O(n) is possible with a set
    duplicates = []
    for i in range(len(items)):
        for j in range(len(items)):
            if i != j and items[i] == items[j]:
                if items[i] not in duplicates:
                    duplicates.append(items[i])
    return duplicates


# ── LOGIC ISSUES ──────────────────────────────────────────────────────────────
def divide(a, b):
    # No zero division check
    return a / b


def get_first_item(lst):
    # No empty list check
    return lst[0]


def parse_config(filepath):
    # Silent failure — returns None on error, callers may not check
    try:
        with open(filepath) as f:
            return json.load(f)
    except:
        pass  # swallows ALL exceptions silently


def count_items(data):
    # Off-by-one: should be range(len(data)), misses last element
    total = 0
    for i in range(len(data) - 1):
        total += data[i]
    return total


# ── STYLE ISSUES ──────────────────────────────────────────────────────────────
def x(a, b, c, d, e):        # single-letter function name, no type hints
    z = a+b                   # no spaces around operator
    y = z*c-d+e               # complex expression, no intermediate vars
    return y                  # single-letter variable names


def ProcessUserData(u, p, r): # PascalCase for function (should be snake_case)
    DATA = u                  # SCREAMING_SNAKE for local var (should be lower)
    RESULT = DATA             # duplicate unnecessary assignment
    return RESULT


class userManager:            # class name not PascalCase
    def __init__(self, x, y, z, a, b, c, d):  # too many params, no type hints
        self.x = x
        self.y = y
        self.z = z
        self.a = a
        self.b = b
        self.c = c
        self.d = d