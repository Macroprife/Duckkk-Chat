"""Duck Chat — admin endpoints (user management, stats)."""

import hashlib
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import db as db_mod

logger = logging.getLogger("myapi.admin")

router = APIRouter(prefix="/api/admin")


async def _require_admin(request: Request) -> str | None:
    raw_token = request.cookies.get("session_token", "")
    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    user = await db_mod.get_user_by_token_hash(token_hash)
    if not user or user.get("role") != "admin" or not user.get("is_active", True):
        return None
    return user["username"]


@router.get("/users")
async def admin_list_users(request: Request, limit: int = 100, offset: int = 0):
    admin = await _require_admin(request)
    if not admin:
        return JSONResponse({"error": "unauthorized"}, status_code=403)
    users = await db_mod.list_users(limit, offset)
    total = await db_mod.count_users_total()
    return {"ok": True, "users": users, "total": total}


@router.patch("/users/{user_id}/role")
async def admin_set_role(user_id: str, request: Request):
    admin = await _require_admin(request)
    if not admin:
        return JSONResponse({"error": "unauthorized"}, status_code=403)
    body = await request.json()
    role = body.get("role", "")
    if role not in ("user", "admin"):
        return JSONResponse({"error": "invalid role"}, status_code=400)
    ok = await db_mod.update_user_role(user_id, role)
    if not ok:
        return JSONResponse({"error": "user not found"}, status_code=404)
    return {"ok": True}


@router.patch("/users/{user_id}/ban")
async def admin_toggle_ban(user_id: str, request: Request):
    admin = await _require_admin(request)
    if not admin:
        return JSONResponse({"error": "unauthorized"}, status_code=403)
    body = await request.json()
    is_active = body.get("is_active", True)
    ok = await db_mod.set_user_active(user_id, bool(is_active))
    if not ok:
        return JSONResponse({"error": "user not found"}, status_code=404)
    return {"ok": True}


@router.get("/stats")
async def admin_stats(request: Request):
    admin = await _require_admin(request)
    if not admin:
        return JSONResponse({"error": "unauthorized"}, status_code=403)
    stats = await db_mod.get_admin_stats()
    recent = await db_mod.get_recent_usage(20)
    return {"ok": True, "stats": stats, "recent_usage": recent}
