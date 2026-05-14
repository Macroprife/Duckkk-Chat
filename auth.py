"""Duck Chat — Auth helpers (password hashing + math captcha + rate limiting + metrics)."""

import os
import random
import hashlib
import logging
import time
from collections import defaultdict

import bcrypt

logger = logging.getLogger("myapi.auth")

# ── Password ─────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ── Harder Math Captcha (multi-step, 2 digits) ──────────────────
# e.g. "37 + 28 = ?" or "15 × 3 - 4 = ?"
# ~1000+ combinations, integer answers guaranteed.

OPS = [
    ("+", lambda a, b: a + b),
    ("-", lambda a, b: a - b),
    ("×", lambda a, b: a * b),
]


def generate_math_captcha() -> tuple[str, int]:
    """Return (question_string, correct_answer) - 2-digit operations only."""
    a = random.randint(11, 99)
    b = random.randint(11, 99)
    op_symbol, op_fn = random.choice(OPS)
    if op_symbol == "-" and a < b:
        a, b = b, a
    answer = op_fn(a, b)
    question = f"{a} {op_symbol} {b} = ?"
    return question, answer


# ── Better Security Questions ───────────────────────────────────

SECURITY_QUESTIONS = [
    "您第一份工作的公司名称是什么？",
    "您出生的医院名称是？",
    "您小学的班主任姓什么？",
    "您第一次旅行的城市是？",
    "您童年最要好的朋友名字是什么？",
]


# ── In-memory Rate Limiting (simple sliding window) ────────────
# For endpoints that don't use slowapi

class MemoryRateLimiter:
    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        bucket = self._buckets[key]
        # Remove expired entries
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        return True


rate_limiter = MemoryRateLimiter()


# ── Session token (for HttpOnly Cookie path) ───────────────────

def generate_session_token() -> tuple[str, str]:
    """Return (raw_token, sha256_hash). Store hash in DB, give raw to client."""
    raw = hashlib.sha256(os.urandom(32)).hexdigest()
    h = hashlib.sha256(raw.encode()).hexdigest()
    return raw, h


# ── Prometheus metrics ──────────────────────────────────────────

from prometheus_client import Counter, Histogram

auth_requests = Counter('duck_auth_requests_total', 'Auth requests by endpoint',
                        ['endpoint', 'status'])
auth_latency = Histogram('duck_auth_latency_seconds', 'Auth API latency',
                         ['endpoint'], buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5])
captcha_generated = Counter('duck_captcha_generated_total', 'Captcha generated')
login_attempts = Counter('duck_login_attempts_total', 'Login attempts by status',
                         ['status'])
rate_limit_exceeded = Counter('duck_rate_limit_exceeded_total', 'Rate limit exceeded',
                              ['endpoint'])
