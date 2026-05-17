"""Duck Chat — misc endpoints (health, metrics, UI, stats, cloud rotation)."""

import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

import db as db_mod
from duckapp.config import ALLOWED_PROVIDERS
from duckapp.services.session import check_cloud_auth

logger = logging.getLogger("myapi.misc")

router = APIRouter()

# ── UI HTML (inline, single-file) ──────────────────────────────

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
  const pwd=prompt("🔑 输入云端密钥：");
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


@router.get("/")
async def home():
    return HTMLResponse(
        '<html><head><meta http-equiv="refresh" content="0;url=/ui"></head></html>'
    )


@router.get("/ui", response_class=HTMLResponse)
async def chat_ui():
    return HTMLResponse(
        UI_HTML,
        headers={
            "Content-Security-Policy":
                "default-src 'self'; script-src 'unsafe-inline' 'self'; "
                "style-src 'unsafe-inline' 'self'; img-src 'self' data:; "
                "connect-src 'self'",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
        },
    )


@router.get("/health")
async def health(request: Request):
    db_ok = False
    try:
        db_mod.pool()
        db_ok = True
    except RuntimeError:
        pass
    return {"ok": True, "db": db_ok}


@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/api/stats/usage")
async def usage_stats(
    request: Request,
    provider: str | None = None,
    model_id: str | None = None,
    days: int = 7,
):
    if not check_cloud_auth(request):
        return JSONResponse({"error": "cloud auth required"}, status_code=401)
    if not getattr(request.app.state, "db_ok", False):
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    if days < 1 or days > 365:
        days = 7
    if provider and provider not in ALLOWED_PROVIDERS:
        return JSONResponse({"error": "invalid provider"}, status_code=400)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        stats = await db_mod.get_model_usage_stats(
            since=since, provider=provider, model_id=model_id, limit=100,
        )
        for s in stats:
            if s.get("avg_duration_ms") is not None:
                s["avg_duration_ms"] = round(float(s["avg_duration_ms"]), 1)
        return {"since": since.isoformat(), "stats": stats}
    except Exception as exc:
        logger.error("usage_stats: %s", exc)
        return JSONResponse({"error": "internal error"}, status_code=500)


@router.get("/api/cloud/rotation-status")
async def cloud_rotation_status(request: Request):
    now = time.time()
    next_at = getattr(request.app.state, "next_rotation_at", now + 60)
    remaining = max(0, next_at - now)
    return {
        "ok": True,
        "next_rotation_at": next_at,
        "seconds_remaining": int(remaining),
        "rotation_version": getattr(request.app.state, "rotation_version", 0),
    }
