"""Duck Chat 🦆 — FastAPI proxy for Ollama / OpenClaw with PostgreSQL persistence."""

import os
import json
import uuid
import logging
import secrets
import time
import ipaddress
import asyncio
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from collections import deque

import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("myapi")

# ── Config ──────────────────────────────────────────────────────

# CRITICAL: never ship a real default key in source. Empty default
# disables cloud auth entirely until SECRET_FILE or env is set.
CLOUD_AUTH_KEY_FALLBACK = os.environ.get("CLOUD_AUTH_KEY", "")
SECRET_FILE = os.environ.get("SECRET_FILE", "/app/secrets/cloud-secret.txt")


def _get_cloud_key() -> str:
    """Read the rotating secret file; fall back to env. Empty string means
    auth is disabled (deny all) — never accept blank keys."""
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


PROVIDERS = {
    "ollama": {
        "base_url": os.environ.get("OLLAMA_URL", "http://localhost:11434/v1"),
        "api_key": os.environ.get("OLLAMA_API_KEY", ""),
    },
    "claw": {
        "base_url": os.environ.get("CLAW_URL", "http://127.0.0.1:18789"),
        # Empty default: disables claw provider until env is set.
        "api_key": os.environ.get("CLAW_API_KEY", ""),
    },
}

REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", os.environ.get("DEEPSEEK_TIMEOUT", "60")))

# CORS — restrict to known origins; "*" disabled by default.
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS", ""
).split(",") if o.strip()]

# Trust X-Forwarded-For only when running behind nginx (default true)
TRUST_FORWARDED_HEADERS = os.environ.get("TRUST_FORWARDED_HEADERS", "1") == "1"


def _client_ip(req: Request) -> str | None:
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
    # Strip IPv6 zone identifiers and validate
    raw = raw.split("%", 1)[0]
    try:
        ipaddress.ip_address(raw)
        return raw
    except ValueError:
        return None


def check_cloud_auth(req: Request) -> bool:
    """Cloud auth — header preferred, query param tolerated for compat."""
    token = req.headers.get("x-cloud-key", "") or req.query_params.get("cloud_key", "")
    return _compare_secret(token, _get_cloud_key())


# ── Rate limiting (in-memory, per-IP, token bucket-ish) ────────

_RATE_BUCKET: dict[str, deque[float]] = {}
_RATE_MAX = int(os.environ.get("AUTH_RATE_LIMIT", "10"))   # max attempts
_RATE_WIN = int(os.environ.get("AUTH_RATE_WINDOW", "60"))  # per N seconds


def _rate_check(ip: str | None) -> bool:
    """Return True if request is allowed; False to deny (429)."""
    if not ip:
        ip = "anon"
    now = time.time()
    bucket = _RATE_BUCKET.setdefault(ip, deque())
    cutoff = now - _RATE_WIN
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX:
        return False
    bucket.append(now)
    return True


# ── Session / Cookie helpers ────────────────────────────────────

SESSION_COOKIE = "duck_sid"
# Cookie idle window — start a new conversation after this much silence
CONVERSATION_IDLE_SECONDS = int(os.environ.get("CONVERSATION_IDLE_SECONDS", "1800"))  # 30 min


def _get_or_create_sid(request: Request) -> tuple[str, bool]:
    """Return (session_id, is_new). Caller must set cookie on the response if new."""
    sid = request.cookies.get(SESSION_COOKIE)
    if sid and re.fullmatch(r"[0-9a-fA-F-]{8,64}", sid):
        return sid, False
    return str(uuid.uuid4()), True


def _set_session_cookie(response: Response, sid: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=sid,
        max_age=86400 * 365,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("COOKIE_SECURE", "0") == "1",
    )


# ── Stream collector ────────────────────────────────────────────

class StreamCollector:
    """Accumulates streamed chunks and persists the final assistant message."""

    def __init__(self, conversation_id: uuid.UUID, session_id: uuid.UUID | None,
                 model_id: str, provider: str, ip: str | None = None):
        self.conversation_id = conversation_id
        self.session_id = session_id
        self.model_id = model_id
        self.provider = provider
        self.ip = ip
        self.chunks: list[str] = []
        self.start_ts = time.perf_counter()
        self.tokens_prompt: int | None = None
        self.tokens_completion: int | None = None

    def add_chunk(self, text: str):
        self.chunks.append(text)

    def finalize_tokens(self, prompt: int | None = None, completion: int | None = None):
        if prompt is not None:
            self.tokens_prompt = prompt
        if completion is not None:
            self.tokens_completion = completion

    @property
    def full_text(self) -> str:
        return "".join(self.chunks)

    @property
    def duration_ms(self) -> int:
        return int((time.perf_counter() - self.start_ts) * 1000)

    async def save(self):
        content = self.full_text
        if not content:
            logger.info("Empty assistant response — skipping persistence")
            return
        try:
            await db.insert_message(
                conversation_id=self.conversation_id,
                role="assistant",
                content=content,
                tokens_prompt=self.tokens_prompt,
                tokens_completion=self.tokens_completion,
                model_id=self.model_id,
                provider=self.provider,
                duration_ms=self.duration_ms,
            )
            await db.insert_usage(
                session_id=self.session_id,
                conversation_id=self.conversation_id,
                model_id=self.model_id,
                provider=self.provider,
                tokens_prompt=self.tokens_prompt or 0,
                tokens_completion=self.tokens_completion or 0,
                duration_ms=self.duration_ms,
                ip_address=self.ip,
            )
            await db.touch_conversation(self.conversation_id)
        except Exception as exc:
            logger.error("Persistence failed: %s", exc)


# ── UI HTML ─────────────────────────────────────────────────────

UI_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Duck Chat 🦆</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;height:100dvh;display:flex;flex-direction:column}
h1{font-size:18px;padding:16px 20px;background:#1e293b;border-bottom:1px solid #334155;display:flex;align-items:center;gap:10px}
h1 span{color:#38bdf8}
.header-right{margin-left:auto;display:flex;align-items:center;gap:8px}
#cloud-btn{background:transparent;border:1px solid #334155;border-radius:6px;color:#94a3b8;padding:4px 10px;font-size:12px;cursor:pointer}
#cloud-btn.auth{border-color:#22c55e;color:#22c55e;background:#052e16}
#model-select{background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:4px 8px;font-size:13px;cursor:pointer}
#model-select:focus{border-color:#38bdf8;outline:none}
#chat{flex:1;overflow-y:auto;padding:16px 20px;display:flex;flex-direction:column;gap:16px}
.msg{max-width:720px;line-height:1.7;white-space:pre-wrap;word-break:break-word;padding:12px 16px;border-radius:12px;animation:fade .2s}
.msg.user{background:#1e3a5f;align-self:flex-end;border-bottom-right-radius:4px}
.msg.assistant{background:#1e293b;align-self:flex-start;border-bottom-left-radius:4px}
.msg.assistant:empty::after{content:"▊";animation:blink .8s infinite}
.msg.error{background:#450a0a;color:#fca5a5;align-self:center}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes blink{50%{opacity:0}}
#form{display:flex;gap:8px;padding:12px 20px;background:#1e293b;border-top:1px solid #334155}
#input{flex:1;padding:10px 14px;border:1px solid #334155;border-radius:8px;background:#0f172a;color:#e2e8f0;font-size:15px;outline:none}
#input:focus{border-color:#38bdf8}
#send{padding:10px 20px;border:none;border-radius:8px;background:#38bdf8;color:#0f172a;font-weight:600;font-size:15px;cursor:pointer}
#send:disabled{opacity:.5;cursor:not-allowed}
#send:hover:not(:disabled){background:#7dd3fc}
.cloud-tag{font-size:9px;color:#38bdf8;margin-left:4px;border:1px solid #38bdf8;border-radius:3px;padding:0 4px}
</style>
</head>
<body>
<h1>🦆 <span>Duck</span> Chat
<div class="header-right">
<button id="cloud-btn">🔒 云端</button>
<select id="model-select"></select>
</div>
</h1>
<div id="chat">
<div class="msg assistant">选择一个模型开始对话</div>
</div>
<form id="form" autocomplete="off">
<input id="input" placeholder="输入消息，回车发送…" autofocus disabled>
<button id="send" type="submit" disabled>发送</button>
</form>
<script>
const chat=document.getElementById("chat"),form=document.getElementById("form"),input=document.getElementById("input"),send=document.getElementById("send"),sel=document.getElementById("model-select"),cloudBtn=document.getElementById("cloud-btn");
let currentModel="",cloudKey=sessionStorage.getItem("cloudKey")||"";
if(cloudKey){cloudBtn.textContent="✅ 云端";cloudBtn.classList.add("auth")}
async function loadModels(showCloud){
  sel.innerHTML="";
  const headers={};
  if(showCloud&&cloudKey)headers["x-cloud-key"]=cloudKey;
  const url=showCloud&&cloudKey?"/models?cloud=1":"/models";
  try{
    const r=await fetch(url,{headers});
    if(r.status===401){alert("❌ 云端密钥已失效，请重新解锁");cloudKey="";sessionStorage.removeItem("cloudKey");cloudBtn.textContent="🔒 云端";cloudBtn.classList.remove("auth");return loadModels(false)}
    const data=await r.json();
    data.models.forEach(g=>{
      const og=document.createElement("optgroup");og.label=g.provider;
      g.models.forEach(m=>{const o=document.createElement("option");o.value=m.id;o.textContent=m.name+(m.size?"  ("+m.size+")":"");og.appendChild(o)});
      sel.appendChild(og)
    });
    if(data.models.length>0&&data.models[0].models.length>0){currentModel=data.models[0].models[0].id;sel.value=currentModel;input.disabled=false;send.disabled=false}
  }catch(e){addMsg("加载失败: "+e.message,"error")}
}
loadModels(!!cloudKey);
cloudBtn.onclick=()=>{
  if(cloudKey){
    if(!confirm("确定锁定云端连接？"))return;
    cloudKey="";sessionStorage.removeItem("cloudKey");cloudBtn.textContent="🔒 云端";cloudBtn.classList.remove("auth");sel.innerHTML="";loadModels(false);return
  }
  const pwd=prompt("🔑 输入云端密钥（cat /tmp/duck-cloud-secret.txt）：");
  if(!pwd)return;
  (async()=>{
    try{
      const r=await fetch("/auth/cloud",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key:pwd})});
      if(r.status===429){alert("❌ 尝试过于频繁，请稍后再试");return}
      if(!r.ok){alert("❌ 密钥错误");return}
      cloudKey=pwd;sessionStorage.setItem("cloudKey",cloudKey);cloudBtn.textContent="✅ 云端";cloudBtn.classList.add("auth");await loadModels(true)
    }catch(e){alert("验证失败: "+e.message)}
  })()
};
sel.onchange=()=>{currentModel=sel.value};
form.onsubmit=async e=>{
  e.preventDefault();const msg=input.value.trim();
  if(!msg||!currentModel)return;
  input.value="";send.disabled=true;addMsg(msg,"user");const bubble=addMsg("","assistant");
  const headers={"Content-Type":"application/json"};
  if(currentModel.startsWith("claw/")&&cloudKey)headers["x-cloud-key"]=cloudKey;
  const body={message:msg,model:currentModel};
  try{
    const r=await fetch("/chat",{method:"POST",headers,body:JSON.stringify(body)});
    if(r.status===401){bubble.textContent="[需要云端密钥]";bubble.className="msg error";cloudKey="";sessionStorage.removeItem("cloudKey");cloudBtn.textContent="🔒 云端";cloudBtn.classList.remove("auth");return}
    if(!r.ok){bubble.textContent="[HTTP "+r.status+"]";bubble.className="msg error";return}
    const reader=r.body.getReader(),dec=new TextDecoder();
    while(true){const{done,value}=await reader.read();if(done)break;bubble.textContent+=dec.decode(value,{stream:true});chat.scrollTop=chat.scrollHeight}
  }catch(e){bubble.textContent="[网络错误: "+e.message+"]";bubble.className="msg error"}
  finally{send.disabled=false;input.focus()}
};
function addMsg(text,role){const d=document.createElement("div");d.className="msg "+role;d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d}
</script>
</body>
</html>"""


# ── App ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout = httpx.Timeout(REQUEST_TIMEOUT, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        app.state.http = client
        app.state.db_ok = False
        try:
            await db.init_pool()
            await db.migrate()
            app.state.db_ok = True
            logger.info("Database ready")
        except Exception as exc:
            logger.warning("Database unavailable: %s", exc)
        logger.info("Duck Chat ready")
        yield
        logger.info("Duck Chat closing")
        if app.state.db_ok:
            await db.close_pool()


app = FastAPI(lifespan=lifespan, title="Duck Chat")

# CORS — never use "*" with credentials. If no origins configured, disable CORS.
if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "x-cloud-key"],
    )


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32000)
    model: str = Field("", max_length=200)


class AuthRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=200)


# ── Auth ────────────────────────────────────────────────────────

@app.post("/auth/cloud")
async def auth_cloud(req: AuthRequest, request: Request):
    ip = _client_ip(request)
    if not _rate_check(ip):
        return JSONResponse({"error": "rate limited"}, status_code=429)
    if _compare_secret(req.key, _get_cloud_key()):
        return {"ok": True}
    logger.warning("Failed auth attempt from %s", ip)
    return JSONResponse({"ok": False}, status_code=403)


@app.get("/")
async def home():
    return HTMLResponse(
        '<html><head><meta http-equiv="refresh" content="0;url=/ui"></head></html>'
    )


@app.get("/health")
async def health():
    db_ok = False
    try:
        db.pool()
        db_ok = True
    except RuntimeError:
        pass
    return {"ok": True, "db": db_ok}


@app.get("/ui", response_class=HTMLResponse)
async def chat_ui():
    return HTMLResponse(
        UI_HTML,
        headers={
            # Defence-in-depth: tight CSP + clickjacking + sniff guards.
            "Content-Security-Policy":
                "default-src 'self'; script-src 'unsafe-inline' 'self'; "
                "style-src 'unsafe-inline' 'self'; img-src 'self' data:; "
                "connect-src 'self'",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
        },
    )


# ── Models ──────────────────────────────────────────────────────

@app.get("/models")
async def list_models(request: Request):
    client: httpx.AsyncClient = app.state.http
    show_cloud = request.query_params.get("cloud") == "1"
    result = []

    # 1) Ollama (always shown — assumed to be on a private network)
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
        # Skip if claw provider isn't configured (no API key)
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
                            "name": f"🧠 {m['id'].replace('openclaw/', '')}",
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


# ── Chat ────────────────────────────────────────────────────────

ALLOWED_PROVIDERS = {"ollama", "claw"}


def _parse_model(model: str) -> tuple[str, str]:
    """Split 'provider/id'. Reject unknown providers."""
    if "/" not in model:
        raise HTTPException(400, "Invalid model id")
    provider, _, name = model.partition("/")
    if provider not in ALLOWED_PROVIDERS or not name:
        raise HTTPException(400, "Invalid model id")
    # Sanity-cap to avoid abuse
    if len(name) > 200:
        raise HTTPException(400, "Model id too long")
    return provider, name


@app.post("/chat")
async def chat(req: ChatRequest, http_request: Request, http_response: Response):
    if not req.model:
        raise HTTPException(400, "model is required")
    provider, _ = _parse_model(req.model)

    # ── Cloud gating: require valid auth header (NOT body field) ──
    if provider == "claw":
        ip = _client_ip(http_request)
        if not _rate_check(ip):
            return JSONResponse({"error": "rate limited"}, status_code=429)
        if not check_cloud_auth(http_request):
            return JSONResponse({"error": "cloud auth required"}, status_code=401)
        if not PROVIDERS["claw"]["api_key"]:
            return JSONResponse({"error": "cloud provider not configured"}, status_code=503)

    # ── DB persistence (best-effort) ──
    db_enabled = getattr(app.state, "db_ok", False)
    session_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    collector: StreamCollector | None = None
    ip = _client_ip(http_request)

    session_key = None
    sid_is_new = False
    if db_enabled:
        try:
            session_key, sid_is_new = _get_or_create_sid(http_request)
            session_id = await db.upsert_session(
                session_key=session_key,
                client_ip=ip,
                user_agent=http_request.headers.get("user-agent"),
            )
            # Reuse recent conversation for the same model when within idle window
            conversation_id = await db.find_or_create_conversation(
                session_id=session_id,
                model_id=req.model,
                provider=provider,
                idle_seconds=CONVERSATION_IDLE_SECONDS,
                first_message_excerpt=req.message[:80],
            )
            await db.insert_message(
                conversation_id=conversation_id,
                role="user",
                content=req.message,
                model_id=req.model,
                provider=provider,
            )
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
    client: httpx.AsyncClient = app.state.http
    if provider == "claw":
        gen = _stream_claw(client, req.model, req.message, collector=collector)
    else:
        gen = _stream_ollama(client, req.model, req.message, collector=collector)

    resp = StreamingResponse(
        gen,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
    if session_key and sid_is_new:
        _set_session_cookie(resp, session_key)
    return resp


async def _stream_ollama(
    client: httpx.AsyncClient,
    model_id: str,
    message: str,
    *,
    collector: StreamCollector | None = None,
) -> AsyncGenerator[str, None]:
    model_name = model_id.split("/", 1)[1]
    cfg = PROVIDERS["ollama"]
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": message}],
        "stream": True,
    }

    try:
        async with client.stream(
            "POST", cfg["base_url"] + "/chat/completions",
            headers=headers, json=payload,
        ) as resp:
            if resp.status_code >= 400:
                yield f"[error {resp.status_code}]"
                return
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                content = line[6:]
                if content == "[DONE]":
                    break
                try:
                    d = json.loads(content)
                    choice = d["choices"][0]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                delta = choice.get("delta", {})
                if "content" in delta:
                    tok = delta["content"]
                    yield tok
                    if collector is not None:
                        collector.add_chunk(tok)
                usage = d.get("usage")
                if usage and collector is not None:
                    collector.finalize_tokens(
                        prompt=usage.get("prompt_tokens"),
                        completion=usage.get("completion_tokens"),
                    )
    except httpx.TimeoutException:
        yield "[timeout]"
    except httpx.HTTPError as e:
        yield f"[network error: {type(e).__name__}]"
    finally:
        if collector is not None:
            try:
                await collector.save()
            except Exception as exc:
                logger.error("collector.save (ollama): %s", exc)


async def _stream_claw(
    client: httpx.AsyncClient,
    model_id: str,
    message: str,
    *,
    collector: StreamCollector | None = None,
) -> AsyncGenerator[str, None]:
    agent = model_id.split("/", 1)[1]
    cfg = PROVIDERS["claw"]
    payload = {
        "model": f"openclaw/{agent}",
        "messages": [{"role": "user", "content": message}],
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    try:
        async with client.stream(
            "POST", cfg["base_url"] + "/v1/chat/completions",
            headers=headers, json=payload,
        ) as resp:
            if resp.status_code >= 400:
                yield f"[claw error {resp.status_code}]"
                return
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                c = line[6:]
                if c == "[DONE]":
                    break
                try:
                    d = json.loads(c)
                    choice = d["choices"][0]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                delta = choice.get("delta", {})
                if "content" in delta:
                    tok = delta["content"]
                    yield tok
                    if collector is not None:
                        collector.add_chunk(tok)
                usage = d.get("usage")
                if usage and collector is not None:
                    collector.finalize_tokens(
                        prompt=usage.get("prompt_tokens"),
                        completion=usage.get("completion_tokens"),
                    )
    except httpx.TimeoutException:
        yield "[timeout]"
    except httpx.HTTPError as e:
        yield f"[network error: {type(e).__name__}]"
    finally:
        if collector is not None:
            try:
                await collector.save()
            except Exception as exc:
                logger.error("collector.save (claw): %s", exc)


# ── History (own session only) ─────────────────────────────────

@app.get("/api/conversations")
async def list_conversations(request: Request, limit: int = 20):
    if limit < 1 or limit > 200:
        limit = 20
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        return {"conversations": []}
    if not getattr(request.app.state, "db_ok", False):
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        row = await db.pool().fetchrow(
            "SELECT id FROM duck.sessions WHERE session_key = $1", sid,
        )
        if not row:
            return {"conversations": []}
        convs = await db.get_session_conversations(row["id"], limit=limit)
        for c in convs:
            c["id"] = str(c["id"])
            for k in ("created_at", "updated_at"):
                if c.get(k) is not None:
                    c[k] = c[k].isoformat()
        return {"conversations": convs}
    except Exception as exc:
        logger.error("list_conversations: %s", exc)
        return JSONResponse({"error": "internal error"}, status_code=500)


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str, request: Request):
    """Return messages of a conversation, but only if it belongs to the caller's session."""
    if not getattr(request.app.state, "db_ok", False):
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        cid = uuid.UUID(conv_id)
    except ValueError:
        return JSONResponse({"error": "invalid id"}, status_code=400)
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        return JSONResponse({"error": "no session"}, status_code=403)
    try:
        # Ownership check
        owner = await db.pool().fetchrow(
            """SELECT 1 FROM duck.conversations c
               JOIN duck.sessions s ON s.id = c.session_id
               WHERE c.id = $1 AND s.session_key = $2""",
            cid, sid,
        )
        if not owner:
            return JSONResponse({"error": "not found"}, status_code=404)
        msgs = await db.get_conversation_messages(cid)
        out = []
        for m in msgs:
            out.append({
                "id": str(m["id"]),
                "role": m["role"],
                "content": m["content"],
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


# ── Stats / Analytics (cloud-auth gated) ───────────────────────

@app.get("/api/stats/usage")
async def usage_stats(
    request: Request,
    provider: str | None = None,
    model_id: str | None = None,
    days: int = 7,
):
    # Stats expose info about all users — protect behind cloud auth.
    if not check_cloud_auth(request):
        return JSONResponse({"error": "cloud auth required"}, status_code=401)
    if not getattr(request.app.state, "db_ok", False):
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    if days < 1 or days > 365:
        days = 7
    if provider and provider not in ALLOWED_PROVIDERS:
        return JSONResponse({"error": "invalid provider"}, status_code=400)
    from datetime import datetime, timedelta, timezone
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        stats = await db.get_model_usage_stats(
            since=since, provider=provider, model_id=model_id, limit=100,
        )
        for s in stats:
            if s.get("avg_duration_ms") is not None:
                s["avg_duration_ms"] = round(float(s["avg_duration_ms"]), 1)
        return {"since": since.isoformat(), "stats": stats}
    except Exception as exc:
        logger.error("usage_stats: %s", exc)
        return JSONResponse({"error": "internal error"}, status_code=500)
