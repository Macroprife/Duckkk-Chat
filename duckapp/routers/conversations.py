"""Duck Chat — conversation CRUD endpoints (list, get, create, rename, delete)."""

import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import db as db_mod
from duckapp.services.session import client_ip, get_or_create_sid, set_session_cookie
from duckapp.config import SESSION_COOKIE

logger = logging.getLogger("myapi.conversations")

router = APIRouter(prefix="/api/conversations")


def _db_check(request: Request):
    if not getattr(request.app.state, "db_ok", False):
        from duckapp.utils.errors import AppError
        raise AppError.service_unavailable("database unavailable")


def _sid(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


async def _session_id(request: Request, sid: str | None) -> uuid.UUID | None:
    if not sid:
        return None
    row = await db_mod.pool().fetchrow(
        "SELECT id FROM duck.sessions WHERE session_key = $1", sid,
    )
    return row["id"] if row else None


async def _check_owner(conv_id: uuid.UUID, sid: str) -> bool:
    row = await db_mod.pool().fetchrow(
        """SELECT 1 FROM duck.conversations c
           JOIN duck.sessions s ON s.id = c.session_id
           WHERE c.id = $1 AND s.session_key = $2""",
        conv_id, sid,
    )
    return row is not None


@router.get("")
async def list_conversations(request: Request, limit: int = 20):
    if limit < 1 or limit > 200:
        limit = 20
    _db_check(request)
    sid = _sid(request)
    if not sid:
        return {"conversations": []}
    try:
        sess_id = await _session_id(request, sid)
        if not sess_id:
            return {"conversations": []}
        convs = await db_mod.get_session_conversations(sess_id, limit=limit)
        for c in convs:
            c["id"] = str(c["id"])
            for k in ("created_at", "updated_at"):
                if c.get(k) is not None:
                    c[k] = c[k].isoformat()
        return {"conversations": convs}
    except Exception as exc:
        logger.error("list_conversations: %s", exc)
        return JSONResponse({"error": "internal error"}, status_code=500)


@router.get("/{conv_id}")
async def get_conversation(conv_id: str, request: Request):
    _db_check(request)
    try:
        cid = uuid.UUID(conv_id)
    except ValueError:
        return JSONResponse({"error": "invalid id"}, status_code=400)
    sid = _sid(request)
    if not sid:
        return JSONResponse({"error": "no session"}, status_code=403)
    try:
        if not await _check_owner(cid, sid):
            return JSONResponse({"error": "not found"}, status_code=404)
        msgs = await db_mod.get_conversation_messages(cid)
        out = []
        for m in msgs:
            meta = m.get("metadata")
            out.append({
                "id": str(m["id"]),
                "role": m["role"],
                "content": m["content"],
                "image": (meta or {}).get("image") if meta else None,
                "tokens_prompt": m.get("tokens_prompt"),
                "tokens_completion": m.get("tokens_completion"),
                "model_id": m.get("model_id"),
                "provider": m.get("provider"),
                "duration_ms": m.get("duration_ms"),
                "created_at": m["created_at"].isoformat() if m.get("created_at") else None,
            })
        return {"messages": out}
    except Exception as exc:
        logger.error("get_conversation: %s", exc)
        return JSONResponse({"error": "internal error"}, status_code=500)


@router.post("")
async def create_conversation(request: Request):
    """Create a new empty conversation and return its ID."""
    _db_check(request)
    body = await request.json()
    model_id = body.get("model_id", "")
    title = body.get("title", "新对话")
    if not model_id:
        return JSONResponse({"error": "model_id is required"}, status_code=400)

    ip = client_ip(request)
    session_key, sid_is_new = get_or_create_sid(request)
    try:
        session_id = await db_mod.upsert_session(
            session_key=session_key,
            client_ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
        cid = await db_mod.create_conversation(
            session_id, model_id, model_id.split("/", 1)[0], title,
        )
        resp = JSONResponse({
            "ok": True,
            "conversation": {
                "id": str(cid),
                "title": title,
                "model_id": model_id,
            },
        })
        if sid_is_new:
            set_session_cookie(resp, session_key)
        return resp
    except Exception as exc:
        logger.error("create_conversation: %s", exc)
        return JSONResponse({"error": "internal error"}, status_code=500)


@router.patch("/{conv_id}")
async def rename_conversation(conv_id: str, request: Request):
    _db_check(request)
    try:
        cid = uuid.UUID(conv_id)
    except ValueError:
        return JSONResponse({"error": "invalid id"}, status_code=400)
    body = await request.json()
    title = (body.get("title") or "").strip()
    if not title:
        return JSONResponse({"error": "title is required"}, status_code=400)
    if len(title) > 200:
        return JSONResponse({"error": "title too long"}, status_code=400)
    sid = _sid(request)
    if not sid:
        return JSONResponse({"error": "no session"}, status_code=403)
    try:
        if not await _check_owner(cid, sid):
            return JSONResponse({"error": "not found"}, status_code=404)
        await db_mod.update_conversation_title(cid, title)
        return {"ok": True}
    except Exception as exc:
        logger.error("rename_conversation: %s", exc)
        return JSONResponse({"error": "internal error"}, status_code=500)


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str, request: Request):
    """Archive (soft-delete) a conversation."""
    _db_check(request)
    try:
        cid = uuid.UUID(conv_id)
    except ValueError:
        return JSONResponse({"error": "invalid id"}, status_code=400)
    sid = _sid(request)
    if not sid:
        return JSONResponse({"error": "no session"}, status_code=403)
    try:
        if not await _check_owner(cid, sid):
            return JSONResponse({"error": "not found"}, status_code=404)
        await db_mod.archive_conversation(cid)
        return {"ok": True}
    except Exception as exc:
        logger.error("delete_conversation: %s", exc)
        return JSONResponse({"error": "internal error"}, status_code=500)
