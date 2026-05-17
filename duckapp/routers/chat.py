"""Duck Chat — model list & chat streaming endpoints."""

import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

import db as db_mod
from duckapp.config import ALLOWED_PROVIDERS, CONVERSATION_IDLE_SECONDS, PROVIDERS
from duckapp.models import ChatRequest
from duckapp.services.session import client_ip, check_cloud_auth, get_or_create_sid, set_session_cookie
from duckapp.services.stream import StreamCollector, stream_claw, stream_ollama

logger = logging.getLogger("myapi.chat")

router = APIRouter()


@router.get("/models")
async def list_models(request: Request):
    show_cloud = request.query_params.get("cloud") == "1"
    client: httpx.AsyncClient = request.app.state.http
    result = []

    # 1) Ollama (always shown — assumed on private network)
    try:
        r = await client.get(
            PROVIDERS["ollama"]["base_url"].rstrip("/").removesuffix("/v1") + "/api/tags",
            timeout=5,
        )
        if r.status_code == 200:
            models = [
                {
                    "id": f"ollama/{m['name']}",
                    "name": m["name"],
                    "size": f"{m.get('size', 0) / 1e9:.1f}GB",
                    "cloud": False,
                }
                for m in r.json().get("models", [])
            ]
            if models:
                result.append({"provider": "🖥 Ollama（本地）", "models": models})
    except Exception as e:
        logger.warning("Ollama list error: %s", e)

    # 2) OpenClaw (gated behind cloud auth)
    if show_cloud:
        if not check_cloud_auth(request):
            return JSONResponse(
                {"error": "cloud auth required", "models": result}, status_code=401
            )
        if PROVIDERS["claw"]["api_key"]:
            try:
                r = await client.get(
                    PROVIDERS["claw"]["base_url"] + "/v1/models",
                    headers={"Authorization": f"Bearer {PROVIDERS['claw']['api_key']}"},
                    timeout=5,
                )
                if r.status_code == 200:
                    models = [
                        {
                            "id": f"claw/{m['id'].replace('openclaw/', '')}",
                            "name": m['id'].replace('openclaw/', ''),
                            "size": "",
                            "cloud": True,
                        }
                        for m in r.json().get("data", [])
                        if m["id"].startswith("openclaw/")
                    ]
                    if models:
                        result.append({"provider": "☁️ OpenClaw（云端）", "models": models})
            except Exception as e:
                logger.warning("Claw list error: %s", e)

    return {"models": result}


def _parse_model(model: str) -> tuple[str, str]:
    """Split 'provider/id'. Reject unknown providers."""
    if "/" not in model:
        from duckapp.utils.errors import AppError
        raise AppError.bad_request("Invalid model id")
    provider, _, name = model.partition("/")
    if provider not in ALLOWED_PROVIDERS or not name:
        from duckapp.utils.errors import AppError
        raise AppError.bad_request("Invalid model id")
    if len(name) > 200:
        from duckapp.utils.errors import AppError
        raise AppError.bad_request("Model id too long")
    return provider, name


@router.post("/chat")
async def chat(req: ChatRequest, http_request: Request, http_response: Response):
    if not req.model:
        from duckapp.utils.errors import AppError
        raise AppError.bad_request("model is required")
    provider, _ = _parse_model(req.model)

    # ── Cloud gating ──
    if provider == "claw":
        ip = client_ip(http_request)
        from duckapp.utils.rate_limit import check_rate
        if not check_rate(ip):
            return JSONResponse({"error": "rate limited"}, status_code=429)
        if not check_cloud_auth(http_request):
            return JSONResponse({"error": "cloud auth required"}, status_code=401)
        if not PROVIDERS["claw"]["api_key"]:
            return JSONResponse({"error": "cloud provider not configured"}, status_code=503)

    # ── DB persistence (best-effort) ──
    db_enabled = getattr(http_request.app.state, "db_ok", False)
    session_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    collector: StreamCollector | None = None
    ip = client_ip(http_request)

    session_key = None
    sid_is_new = False
    if db_enabled:
        try:
            session_key, sid_is_new = get_or_create_sid(http_request)
            session_id = await db_mod.upsert_session(
                session_key=session_key,
                client_ip=ip,
                user_agent=http_request.headers.get("user-agent"),
            )

            if req.conversation_id:
                try:
                    cid = uuid.UUID(req.conversation_id)
                except ValueError:
                    from duckapp.utils.errors import AppError
                    raise AppError.bad_request("invalid conversation_id")
                conv = await db_mod.get_conversation_by_id(cid, session_id)
                if not conv:
                    from duckapp.utils.errors import AppError
                    raise AppError.not_found("conversation not found")
                conversation_id = cid
            else:
                conversation_id = await db_mod.find_or_create_conversation(
                    session_id=session_id,
                    model_id=req.model,
                    provider=provider,
                    idle_seconds=CONVERSATION_IDLE_SECONDS,
                    first_message_excerpt=req.message[:80],
                )

            await db_mod.insert_message(
                conversation_id=conversation_id,
                role="user",
                content=req.message,
                model_id=req.model,
                provider=provider,
                metadata={"image": req.image} if (req.image and req.image.startswith("data:image")) else None,
            )

            if str(conversation_id) == req.conversation_id:
                conv_data = await db_mod.get_conversation_by_id(conversation_id, session_id)
                if conv_data and conv_data.get("title") == "新对话":
                    await db_mod.update_conversation_title(conversation_id, req.message[:80])

            collector = StreamCollector(
                conversation_id=conversation_id,
                session_id=session_id,
                model_id=req.model,
                provider=provider,
                ip=ip,
            )
        except Exception as exc:
            logger.error("DB error during chat setup: %s", exc)
            collector = None

    # ── Stream ──
    client: httpx.AsyncClient = http_request.app.state.http
    image = req.image if req.image and req.image.startswith("data:image") else None
    if provider == "claw":
        gen = stream_claw(client, req.model, req.message, image=image, collector=collector)
    else:
        gen = stream_ollama(client, req.model, req.message, image=image, collector=collector)

    resp = StreamingResponse(
        gen,
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Conversation-Id": str(conversation_id) if conversation_id else "",
        },
    )
    if session_key and sid_is_new:
        set_session_cookie(resp, session_key)
    return resp
