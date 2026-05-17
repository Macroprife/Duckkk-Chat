"""Duck Chat — authentication & user management endpoints."""

import hashlib
import logging
import re

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import db as db_mod
import auth as auth_mod
from duckapp.models import AuthRequest
from duckapp.services.session import client_ip, check_cloud_auth
from duckapp.utils.rate_limit import check_rate
from duckapp.config import SESSION_COOKIE, COOKIE_SECURE

logger = logging.getLogger("myapi.auth")

router = APIRouter()

limiter = Limiter(key_func=get_remote_address)


# ── /auth/cloud (original, for the "simple" HTML UI) ──────────

@router.post("/auth/cloud")
async def auth_cloud(req: AuthRequest, request: Request):
    ip = client_ip(request)
    if not check_rate(ip):
        return JSONResponse({"error": "rate limited"}, status_code=429)
    from duckapp.services.session import _compare_secret, _get_cloud_key
    if _compare_secret(req.key, _get_cloud_key()):
        return {"ok": True}
    logger.warning("Failed auth attempt from %s", ip)
    return JSONResponse({"ok": False}, status_code=403)


# ── /api/auth endpoints (Vue SPA path) ────────────────────────

@router.post("/api/auth/check-username")
@limiter.limit("30/minute")
async def check_username(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    if not username:
        return {"exists": False}
    user = await db_mod.get_user_by_username(username)
    return {"exists": user is not None}


@router.post("/api/auth/captcha")
@limiter.limit("10/minute")
async def get_captcha(request: Request):
    auth_mod.captcha_generated.inc()
    question, answer = auth_mod.generate_math_captcha()
    return JSONResponse({"question": question, "answer": answer})


@router.post("/api/auth/register")
@limiter.limit("5/hour")
async def register(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    sec_q = (body.get("security_question") or "").strip()
    sec_a = (body.get("security_answer") or "").strip()

    if not username or len(username) > 8:
        return JSONResponse({"error": "用户名不超过8个字符"}, status_code=400)
    if not re.match(r"^[a-zA-Z0-9]+$", username):
        return JSONResponse({"error": "用户名只能包含字母和数字"}, status_code=400)
    if len(password) < 8:
        return JSONResponse({"error": "密码不少于8个字符"}, status_code=400)
    if sec_q not in auth_mod.SECURITY_QUESTIONS:
        return JSONResponse({"error": "无效的密保问题"}, status_code=400)
    if not sec_a:
        return JSONResponse({"error": "密保答案不能为空"}, status_code=400)
    if not getattr(request.app.state, "db_ok", False):
        return JSONResponse({"error": "数据库不可用"}, status_code=503)

    existing_users = await db_mod.count_users()
    if existing_users >= 500:
        return JSONResponse({"error": "注册名额已满(上限500)"}, status_code=403)

    pw_hash = auth_mod.hash_password(password)
    sec_hash = auth_mod.hash_password(sec_a)
    user = await db_mod.create_user(username, pw_hash, sec_q, sec_hash)
    if not user:
        return JSONResponse({"error": "该用户名已被注册"}, status_code=409)

    if existing_users == 0:
        await db_mod.update_user_role(str(user["id"]), "admin")
        role = "admin"
    else:
        role = "user"

    auth_mod.auth_requests.labels(endpoint="register", status="success").inc()
    return {"ok": True, "username": user["username"], "role": role}


@router.post("/api/auth/login")
@limiter.limit("10/5minute")
async def login(request: Request, response: Response):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return JSONResponse({"error": "请输入用户名和密码"}, status_code=400)
    user = await db_mod.get_user_by_username(username)
    if not user:
        return JSONResponse({"error": "未检索到该账号，请注册"}, status_code=404)
    if not auth_mod.check_password(password, user["password_hash"]):
        auth_mod.login_attempts.labels(status="failure").inc()
        return JSONResponse({"error": "密码错误"}, status_code=401)

    raw_token, token_hash = auth_mod.generate_session_token()
    await db_mod.set_user_token(username, token_hash)

    response.set_cookie(
        key="session_token",
        value=raw_token,
        max_age=7 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )

    auth_mod.login_attempts.labels(status="success").inc()
    auth_mod.auth_requests.labels(endpoint="login", status="success").inc()
    return {
        "ok": True,
        "username": user["username"],
        "role": user.get("role", "user"),
    }


@router.post("/api/auth/verify")
@limiter.limit("30/minute")
async def verify_token(request: Request):
    raw_token = request.cookies.get("session_token", "")
    body = await request.json()
    username = (body.get("username") or "").strip().lower()

    if not raw_token or not username:
        return {"valid": False}

    stored_hash = await db_mod.get_user_token_hash(username)
    if not stored_hash:
        return {"valid": False}

    given_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return {"valid": given_hash == stored_hash}


@router.post("/api/auth/security")
@limiter.limit("20/minute")
async def get_security_question(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    if not username:
        return JSONResponse({"error": "请输入用户名"}, status_code=400)
    user = await db_mod.get_user_by_username(username)
    if not user:
        return JSONResponse({"error": "该账号不存在"}, status_code=404)
    return {"question": user.get("security_question", "")}


@router.post("/api/auth/verify-security")
@limiter.limit("10/minute")
async def verify_security(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    answer = (body.get("answer") or "").strip()
    if not username or not answer:
        return JSONResponse({"error": "参数不完整"}, status_code=400)
    user = await db_mod.get_user_by_username(username)
    if not user:
        return JSONResponse({"error": "该账号不存在"}, status_code=404)
    stored_hash = user.get("security_answer", "")
    if not stored_hash or not auth_mod.check_password(answer, stored_hash):
        return {"ok": False}
    return {"ok": True}


@router.post("/api/auth/reset-password")
@limiter.limit("5/hour")
async def reset_password(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    new_password = body.get("new_password") or ""
    if not username or len(new_password) < 8:
        return JSONResponse({"error": "密码不少于8个字符"}, status_code=400)
    user = await db_mod.get_user_by_username(username)
    if not user:
        return JSONResponse({"error": "该账号不存在"}, status_code=404)
    if auth_mod.check_password(new_password, user["password_hash"]):
        return JSONResponse({"error": "新密码不能与原密码一致"}, status_code=400)
    pw_hash = auth_mod.hash_password(new_password)
    await db_mod.update_user_password(username, pw_hash)
    return {"ok": True}
