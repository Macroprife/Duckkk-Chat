"""Duck Chat — configuration (env vars, constants, providers)."""

import os

# ── Providers ───────────────────────────────────────────────────

PROVIDERS = {
    "ollama": {
        "base_url": os.environ.get("OLLAMA_URL", "http://localhost:11434/v1"),
        "api_key": os.environ.get("OLLAMA_API_KEY", ""),
    },
    "claw": {
        "base_url": os.environ.get("CLAW_URL", "http://127.0.0.1:18789"),
        "api_key": os.environ.get("CLAW_API_KEY", ""),
    },
}

ALLOWED_PROVIDERS = {"ollama", "claw"}

# ── Cloud auth ──────────────────────────────────────────────────

CLOUD_AUTH_KEY_FALLBACK = os.environ.get("CLOUD_AUTH_KEY", "")
SECRET_FILE = os.environ.get("SECRET_FILE", "/app/secrets/cloud-secret.txt")
SECRET_ROTATION_INTERVAL = 1800  # 30 minutes

# ── Timeouts ────────────────────────────────────────────────────

REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", os.environ.get("DEEPSEEK_TIMEOUT", "60")))

# ── CORS ────────────────────────────────────────────────────────

ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS", ""
).split(",") if o.strip()]

# ── Session / Cookie ────────────────────────────────────────────

SESSION_COOKIE = "duck_sid"
CONVERSATION_IDLE_SECONDS = int(os.environ.get("CONVERSATION_IDLE_SECONDS", "1800"))  # 30 min
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"

# ── Rate limiting ───────────────────────────────────────────────

AUTH_RATE_MAX = int(os.environ.get("AUTH_RATE_LIMIT", "10"))
AUTH_RATE_WINDOW = int(os.environ.get("AUTH_RATE_WINDOW", "60"))

# ── Network ─────────────────────────────────────────────────────

TRUST_FORWARDED_HEADERS = os.environ.get("TRUST_FORWARDED_HEADERS", "1") == "1"
