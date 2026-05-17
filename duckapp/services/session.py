"""Duck Chat — session / cookie helpers."""

import re
import uuid
import os
import secrets

from fastapi import Request, Response
import ipaddress

from duckapp.config import SESSION_COOKIE, COOKIE_SECURE, TRUST_FORWARDED_HEADERS


def client_ip(req: Request) -> str | None:
    """Resolve the real client IP (XFF aware), validated as a real IP."""
    raw = None
    if TRUST_FORWARDED_HEADERS:
        xff = req.headers.get("x-forwarded-for", "")
        if xff:
            raw = xff.split(",")[0].strip()
    if not raw and req.client:
        raw = req.client.host
    if not raw:
        return None
    raw = raw.split("%", 1)[0]
    try:
        ipaddress.ip_address(raw)
        return raw
    except ValueError:
        return None


def get_or_create_sid(request: Request) -> tuple[str, bool]:
    """Return (session_id, is_new). Caller must set cookie on the response if new."""
    sid = request.cookies.get(SESSION_COOKIE)
    if sid and re.fullmatch(r"[0-9a-fA-F-]{8,64}", sid):
        return sid, False
    return str(uuid.uuid4()), True


def set_session_cookie(response: Response, sid: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=sid,
        max_age=86400 * 365,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )


def check_cloud_auth(req: Request) -> bool:
    """Cloud auth — header preferred, query param tolerated for compat."""
    token = req.headers.get("x-cloud-key", "") or req.query_params.get("cloud_key", "")
    return _compare_secret(token, _get_cloud_key())


def _get_cloud_key() -> str:
    """Read the rotating secret file; fall back to env. Empty string means
    auth is disabled (deny all) — never accept blank keys."""
    from duckapp.config import SECRET_FILE, CLOUD_AUTH_KEY_FALLBACK
    try:
        with open(SECRET_FILE) as f:
            key = f.read().strip()
            if key:
                return key
    except (FileNotFoundError, OSError):
        pass
    return CLOUD_AUTH_KEY_FALLBACK


def _compare_secret(a: str, b: str) -> bool:
    """Constant-time compare with empty-string guard (both empty is NOT ok)."""
    if not a or not b:
        return False
    return secrets.compare_digest(a, b)
