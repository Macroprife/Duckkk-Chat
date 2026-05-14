"""Duck Chat — Auth helpers (password hashing + math captcha)."""

import os
import random
import bcrypt

# ── Password ─────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ── Math Captcha ────────────────────────────────────────────────
# Simple single-digit arithmetic, integer answer guaranteed.

OPS = [
    ("+", lambda a, b: a + b),
    ("-", lambda a, b: a - b),
    ("×", lambda a, b: a * b),
]


def generate_math_captcha() -> tuple[str, int]:
    """Return (question_string, correct_answer)."""
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    op_symbol, op_fn = random.choice(OPS)

    # Ensure non-negative for subtraction
    if op_symbol == "-":
        if a < b:
            a, b = b, a

    answer = op_fn(a, b)
    question = f"{a} {op_symbol} {b} = ?"
    return question, answer


def verify_math_captcha(question: str, user_answer: int) -> bool:
    """Recompute and check answer."""
    # Parse question like "3 + 5 = ?"
    parts = question.strip(" ?").split()
    if len(parts) != 3:
        return False
    try:
        a = int(parts[0])
        op = parts[1]
        b = int(parts[2])
    except (ValueError, IndexError):
        return False

    ops_map = {"+": lambda x, y: x + y, "-": lambda x, y: x - y, "×": lambda x, y: x * y}
    fn = ops_map.get(op)
    if not fn:
        return False
    return fn(a, b) == user_answer


# ── Session token ──────────────────────────────────────────────


def generate_session_token() -> tuple[str, str]:
    """Return (raw_token, sha256_hash). Store hash in DB, give raw to client."""
    import hashlib, os
    raw = hashlib.sha256(os.urandom(32)).hexdigest()
    h = hashlib.sha256(raw.encode()).hexdigest()
    return raw, h
