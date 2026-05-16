from backend.models.schemas import ReviewResponse, AgentReview, Issue, Severity


def get_mock_review() -> ReviewResponse:
    return ReviewResponse(
        security=AgentReview(
            agent_name="SecurityAgent",
            score=32,
            summary="Critical SQL injection vulnerability and weak token generation detected. Immediate remediation required before merge.",
            issues=[
                Issue(
                    line="3",
                    severity=Severity.CRITICAL,
                    description="SQL injection via string concatenation in login query. Attacker can bypass authentication with ' OR '1'='1.",
                    suggestion="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))"
                ),
                Issue(
                    line="7",
                    severity=Severity.HIGH,
                    description="Weak session token generated using username + timestamp. Predictable and brute-forceable.",
                    suggestion="Use secrets.token_hex(32) or uuid.uuid4() for cryptographically secure token generation."
                ),
                Issue(
                    line="7",
                    severity=Severity.HIGH,
                    description="Plain-text password comparison. Passwords must never be stored or compared in plain text.",
                    suggestion="Use bcrypt or argon2: bcrypt.checkpw(password.encode(), stored_hash)"
                ),
            ]
        ),
        performance=AgentReview(
            agent_name="PerformanceAgent",
            score=41,
            summary="O(n²) nested loop and full table scan identified. Will not scale beyond a few hundred records.",
            issues=[
                Issue(
                    line="18",
                    severity=Severity.HIGH,
                    description="Full table scan in get_user_data(): fetches ALL users from DB then filters in Python. O(n) memory, O(n) time.",
                    suggestion="Query directly: cursor.execute('SELECT * FROM users WHERE id=?', (user_id,)) — O(1) with indexed id."
                ),
                Issue(
                    line="23",
                    severity=Severity.HIGH,
                    description="O(n²) nested loop in process_items(). For n=1000 items this runs 1,000,000 iterations.",
                    suggestion="Clarify intent. If computing all pairs use itertools.combinations(items, 2). If something else, flatten the logic."
                ),
                Issue(
                    line="18",
                    severity=Severity.MEDIUM,
                    description="No pagination or LIMIT on DB query. Will load entire users table into memory.",
                    suggestion="Add LIMIT clause or use cursor pagination for production queries."
                ),
            ]
        ),
        logic=AgentReview(
            agent_name="LogicAgent",
            score=55,
            summary="Missing null checks and silent failure modes. Edge cases around empty inputs not handled.",
            issues=[
                Issue(
                    line="4",
                    severity=Severity.MEDIUM,
                    description="No input validation on username/password. Empty string or None inputs will cause DB errors.",
                    suggestion="Add guard: if not username or not password: raise ValueError('Credentials required')"
                ),
                Issue(
                    line="9",
                    severity=Severity.MEDIUM,
                    description="Function returns None on failed login with no error context. Caller cannot distinguish DB error from wrong password.",
                    suggestion="Raise AuthenticationError or return a typed result object instead of bare None."
                ),
                Issue(
                    line="17",
                    severity=Severity.LOW,
                    description="get_user_data() returns None silently if user not found. No logging, no exception.",
                    suggestion="Add logging: logger.warning(f'User {user_id} not found') and consider raising UserNotFoundError."
                ),
            ]
        ),
        style=AgentReview(
            agent_name="StyleAgent",
            score=60,
            summary="Missing type hints, docstrings, and inconsistent naming. Code is functional but not production-grade readable.",
            issues=[
                Issue(
                    line="1",
                    severity=Severity.LOW,
                    description="No type hints on any function. authenticate_user(username, password) should be annotated.",
                    suggestion="def authenticate_user(username: str, password: str) -> dict | None:"
                ),
                Issue(
                    line="1",
                    severity=Severity.LOW,
                    description="No docstrings on any function. Purpose, args, and return values are undocumented.",
                    suggestion="Add Google-style or NumPy-style docstrings to all public functions."
                ),
                Issue(
                    line="22",
                    severity=Severity.INFO,
                    description="process_items() is a vague name. Does not describe what is being processed or why.",
                    suggestion="Rename to describe intent: compute_item_pairs(), merge_item_combinations(), etc."
                ),
            ]
        ),
        final_recommendation="❌ Do NOT merge. This code has a critical SQL injection vulnerability (line 3) that allows complete authentication bypass — this is a P0 security issue. Additionally, the O(n²) loop and full table scan will cause severe performance degradation at scale. Fix the SQL injection with parameterized queries, replace the token generation with secrets.token_hex(32), and rewrite get_user_data() to query by ID directly. Re-submit for review after these three issues are resolved.",
        overall_score=47,
        total_issues=9,
    )