"""Duck Chat — FastAPI application factory."""

import asyncio
import logging
import os
import secrets
import tempfile
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import db as db_mod
import auth as auth_mod
from duckapp.config import (
    ALLOWED_ORIGINS, REQUEST_TIMEOUT, SECRET_FILE, SECRET_ROTATION_INTERVAL,
    CLOUD_AUTH_KEY_FALLBACK,
)
from duckapp.utils.errors import AppError, app_error_handler, generic_error_handler

logger = logging.getLogger("myapi")

CLOUD_AUTH_KEY_FALLBACK = CLOUD_AUTH_KEY_FALLBACK


def _get_cloud_key() -> str:
    try:
        with open(SECRET_FILE) as f:
            key = f.read().strip()
            if key:
                return key
    except (FileNotFoundError, OSError):
        pass
    return CLOUD_AUTH_KEY_FALLBACK


def _write_secret(content: str):
    try:
        tmp = tempfile.NamedTemporaryFile(
            dir=os.path.dirname(SECRET_FILE),
            prefix=".cloud-secret.",
            delete=False,
            mode="w",
        )
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, SECRET_FILE)
    except OSError as exc:
        logger.error("secret write failed: %s", exc)


async def _secret_rotator(app_state):
    app_state.rotation_version = 0
    if not _get_cloud_key():
        _write_secret(secrets.token_hex(8))
    app_state.next_rotation_at = time.time() + SECRET_ROTATION_INTERVAL

    while True:
        await asyncio.sleep(SECRET_ROTATION_INTERVAL)
        new_secret = secrets.token_hex(8)
        _write_secret(new_secret)
        app_state.rotation_version += 1
        app_state.next_rotation_at = time.time() + SECRET_ROTATION_INTERVAL
        logger.info("Cloud secret rotated (v%d)", app_state.rotation_version)


limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    """Build and return the Duck Chat FastAPI application."""

    from duckapp.routers import auth, chat, conversations, admin, misc

    @limiter.limit("100/minute")
    async def _dummy(request: Request):
        pass

    async def lifespan(app: FastAPI):
        timeout = httpx.Timeout(REQUEST_TIMEOUT, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            app.state.http = client
            app.state.db_ok = False
            app.state.next_rotation_at = time.time() + SECRET_ROTATION_INTERVAL
            try:
                await db_mod.init_pool()
                await db_mod.migrate()
                app.state.db_ok = True
                logger.info("Database ready")
            except Exception as exc:
                logger.warning("Database unavailable: %s", exc)

            rotator_task = asyncio.create_task(_secret_rotator(app.state))

            logger.info("Duck Chat ready")
            yield
            logger.info("Duck Chat closing")
            rotator_task.cancel()
            try:
                await rotator_task
            except asyncio.CancelledError:
                pass
            if app.state.db_ok:
                await db_mod.close_pool()

    app = FastAPI(lifespan=lifespan, title="Duck Chat")

    # ── CORS ──
    if ALLOWED_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "x-cloud-key"],
        )

    # ── Error handlers ──
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc):
        auth_mod.rate_limit_exceeded.labels(endpoint=request.url.path).inc()
        return JSONResponse({"error": "请求过于频繁，请稍后再试"}, status_code=429)

    # ── Register routers ──
    app.include_router(misc.router)          # /health, /metrics, /ui, /, /api/stats/usage, /api/cloud/rotation-status
    app.include_router(auth.router)          # /auth/cloud, /api/auth/*
    app.include_router(chat.router)          # /models, /chat
    app.include_router(conversations.router) # /api/conversations/{...}
    app.include_router(admin.router)         # /api/admin/{...}

    return app
