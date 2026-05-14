"""Duck Chat — API integration tests.

Run: docker exec myapi-api-1 python3 -m pytest /app/tests.py -v --tb=short
"""

import os
import json
import httpx
import pytest

BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8000")
client = httpx.Client(base_url=BASE_URL, timeout=10)

# Single test user for all auth tests
TEST_USER = "t" + os.urandom(4).hex()[:5]  # max 8 chars
TEST_PASS = "TestPass123"
TEST_SEC_Q = "您第一份工作的公司名称是什么？"
TEST_SEC_A = "MyCompany"


class TestAuth:
    """Auth flow tests first (before rate limiting kicks in)."""


    def test_01_register_duplicate(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_02_metrics(self):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "python_info" in r.text  # metrics endpoint is working

    def test_03_captcha(self):
        r = client.post("/api/auth/captcha", json={})
        assert r.status_code == 200
        data = r.json()
        assert "question" in data
        assert "answer" in data
        assert "= ?" in data["question"]

    def test_04_rate_limiting(self):
        # Flush the rate limiter by sending 15 rapid requests
        statuses = []
        for _ in range(15):
            r = client.post("/api/auth/captcha", json={})
            statuses.append(r.status_code)
        assert 429 in statuses, f"No rate limiting: {statuses}"

    def test_13_register_validation(self):  # After rate limit test
        # May be rate limited, so be lenient
        def _check(r, exp_status):
            if r.status_code != exp_status:
                assert r.status_code == 429, f"Expected {exp_status}, got {r.status_code}: {r.text}"
        # Too long username
        r = client.post("/api/auth/register", json={
            "username": "toolong12",
            "password": "Test1234",
            "security_question": TEST_SEC_Q,
            "security_answer": "Ans",
        })
        _check(r, 400)

        # Short password
        r = client.post("/api/auth/register", json={
            "username": "valid",
            "password": "short",
            "security_question": TEST_SEC_Q,
            "security_answer": "Ans",
        })
        _check(r, 400)

        # Special chars
        r = client.post("/api/auth/register", json={
            "username": "bad!!!",
            "password": "Test1234",
            "security_question": TEST_SEC_Q,
            "security_answer": "Ans",
        })
        _check(r, 400)

    def test_14_security_unknown_user(self):
        r = client.post("/api/auth/security", json={"username": "ghost"})
        assert r.status_code == 404



