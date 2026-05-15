"""Duck Chat — PostgreSQL data layer.

Tables (schema `duck`):
  sessions      — browser sessions / clients
  conversations — chat conversations (grouped messages)
  messages      — individual chat turns
  usage_stats   — token usage per model
"""

import os
import uuid
import json
import logging
import ipaddress
from typing import Optional
from datetime import datetime

import asyncpg
from asyncpg import Pool

logger = logging.getLogger("myapi.db")

_pool: Optional[Pool] = None

DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://duck:duck@127.0.0.1:5432/duck",
)


# ── Schema DDL ─────────────────────────────────────────────────

# NOTE: `cloud_key` column was DROPPED from sessions in v2 — never store
# the rotating secret in the database (no auth value, large blast radius
# on db dump). We keep `cloud_authed` for telemetry only.
SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS duck;

CREATE TABLE IF NOT EXISTS duck.sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_key     TEXT UNIQUE,
    client_ip       INET,
    user_agent      TEXT,
    cloud_authed    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- v1 had a cloud_key column. Drop it if present (no-op if absent).
ALTER TABLE duck.sessions DROP COLUMN IF EXISTS cloud_key;

CREATE TABLE IF NOT EXISTS duck.conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES duck.sessions(id) ON DELETE CASCADE,
    title           TEXT,
    model_id        TEXT NOT NULL,
    provider        TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS duck.messages (
    id                BIGSERIAL PRIMARY KEY,
    conversation_id   UUID NOT NULL REFERENCES duck.conversations(id) ON DELETE CASCADE,
    role              TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content           TEXT NOT NULL DEFAULT '',
    tokens_prompt     INTEGER,
    tokens_completion INTEGER,
    model_id          TEXT,
    provider          TEXT,
    duration_ms       INTEGER,
    metadata          JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS duck.usage_stats (
    id                BIGSERIAL PRIMARY KEY,
    session_id        UUID REFERENCES duck.sessions(id) ON DELETE SET NULL,
    conversation_id   UUID REFERENCES duck.conversations(id) ON DELETE SET NULL,
    model_id          TEXT NOT NULL,
    provider          TEXT NOT NULL,
    tokens_prompt     INTEGER NOT NULL DEFAULT 0,
    tokens_completion INTEGER NOT NULL DEFAULT 0,
    total_tokens      INTEGER GENERATED ALWAYS AS (tokens_prompt + tokens_completion) STORED,
    duration_ms       INTEGER,
    ip_address        INET,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conv         ON duck.messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON duck.conversations(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_recent  ON duck.conversations(session_id, model_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_stats_created   ON duck.usage_stats(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_stats_model     ON duck.usage_stats(model_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_provider  ON duck.usage_stats(provider);

-- v3: archived_at for conversation cleanup (no cascade data loss)

-- v4: user accounts for auth gate
CREATE TABLE IF NOT EXISTS duck.users (
    token_hash      TEXT,
    security_question TEXT,
    security_answer  TEXT,
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE duck.conversations ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
ALTER TABLE duck.users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user';
ALTER TABLE duck.users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

"""


# ── Pool lifecycle ─────────────────────────────────────────────

async def init_pool(dsn: str | None = None) -> Pool:
    global _pool
    dsn = dsn or DSN
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=1,
        max_size=10,
        command_timeout=10,
    )
    safe_dsn = dsn
    if "@" in safe_dsn:
        # mask credentials in log
        scheme, _, rest = safe_dsn.partition("://")
        if "@" in rest:
            safe_dsn = f"{scheme}://***:***@{rest.split('@', 1)[1]}"
    logger.info("DB pool created: %s", safe_dsn)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("DB pool closed")


def pool() -> Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialised")
    return _pool


async def migrate():
    async with pool().acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logger.info("Schema migration applied")


# ── Helpers ────────────────────────────────────────────────────

def _safe_inet(value: str | None) -> str | None:
    """Validate a string as IPv4/IPv6 before passing to asyncpg's INET."""
    if not value:
        return None
    raw = value.split("%", 1)[0]  # strip IPv6 zone
    try:
        ipaddress.ip_address(raw)
        return raw
    except ValueError:
        return None


# ── Session helpers ────────────────────────────────────────────

async def upsert_session(
    session_key: str,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> uuid.UUID:
    """Atomic upsert keyed by session_key. Avoids race conditions."""
    ip = _safe_inet(client_ip)
    row = await pool().fetchrow(
        """
        INSERT INTO duck.sessions (session_key, client_ip, user_agent)
        VALUES ($1, $2::inet, $3)
        ON CONFLICT (session_key) DO UPDATE
            SET updated_at = now(),
                client_ip = COALESCE(EXCLUDED.client_ip, duck.sessions.client_ip),
                user_agent = COALESCE(EXCLUDED.user_agent, duck.sessions.user_agent)
        RETURNING id
        """,
        session_key, ip, user_agent,
    )
    return row["id"]


async def mark_cloud_authed(session_id: uuid.UUID):
    """Telemetry only — flag that this session has used cloud."""
    await pool().execute(
        "UPDATE duck.sessions SET cloud_authed = TRUE, updated_at = now() WHERE id = $1",
        session_id,
    )


# ── Conversation helpers ───────────────────────────────────────

async def find_or_create_conversation(
    session_id: uuid.UUID,
    model_id: str,
    provider: str,
    *,
    idle_seconds: int = 1800,
    first_message_excerpt: str | None = None,
) -> uuid.UUID:
    """Reuse the most-recent conversation for the same model within the
    idle window; otherwise start a new one."""
    row = await pool().fetchrow(
        """
        SELECT id FROM duck.conversations
        WHERE session_id = $1
          AND model_id = $2
          AND updated_at > now() - ($3 || ' seconds')::interval
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        session_id, model_id, str(idle_seconds),
    )
    if row:
        return row["id"]

    new = await pool().fetchrow(
        """
        INSERT INTO duck.conversations (session_id, title, model_id, provider)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        session_id, first_message_excerpt, model_id, provider,
    )
    return new["id"]


async def touch_conversation(conversation_id: uuid.UUID):
    """Bump updated_at after a turn finishes."""
    await pool().execute(
        "UPDATE duck.conversations SET updated_at = now() WHERE id = $1",
        conversation_id,
    )


async def get_active_conversation(session_id: uuid.UUID) -> uuid.UUID | None:
    row = await pool().fetchrow(
        "SELECT id FROM duck.conversations WHERE session_id = $1 ORDER BY updated_at DESC LIMIT 1",
        session_id,
    )
    return row["id"] if row else None


# ── Multi-session management ────────────────────────────────────

async def create_conversation(
    session_id: uuid.UUID,
    model_id: str,
    provider: str,
    title: str | None = None,
) -> uuid.UUID:
    row = await pool().fetchrow(
        """
        INSERT INTO duck.conversations (session_id, title, model_id, provider)
        VALUES ($1, $2, $3, $4)
        RETURNING id, created_at, updated_at
        """,
        session_id, title or "新对话", model_id, provider,
    )
    return row["id"]


async def update_conversation_title(conversation_id: uuid.UUID, title: str) -> bool:
    result = await pool().execute(
        "UPDATE duck.conversations SET title = $1, updated_at = now() WHERE id = $2",
        title, conversation_id,
    )
    return result != "UPDATE 0"


async def archive_conversation(conversation_id: uuid.UUID) -> bool:
    result = await pool().execute(
        "UPDATE duck.conversations SET archived_at = now() WHERE id = $1 AND archived_at IS NULL",
        conversation_id,
    )
    return result != "UPDATE 0"


async def get_conversation_by_id(conversation_id: uuid.UUID, session_id: uuid.UUID) -> dict | None:
    row = await pool().fetchrow(
        """
        SELECT id, title, model_id, provider, created_at, updated_at
        FROM duck.conversations
        WHERE id = $1 AND session_id = $2 AND archived_at IS NULL
        """,
        conversation_id, session_id,
    )
    return dict(row) if row else None


# ── Message helpers ────────────────────────────────────────────

async def insert_message(
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    tokens_prompt: int | None = None,
    tokens_completion: int | None = None,
    model_id: str | None = None,
    provider: str | None = None,
    duration_ms: int | None = None,
    metadata: dict | None = None,
) -> int:
    if role not in ("user", "assistant", "system"):
        raise ValueError(f"invalid role: {role}")
    row = await pool().fetchrow(
        """
        INSERT INTO duck.messages
            (conversation_id, role, content, tokens_prompt, tokens_completion,
             model_id, provider, duration_ms, metadata)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
        RETURNING id
        """,
        conversation_id, role, content,
        tokens_prompt, tokens_completion,
        model_id, provider, duration_ms,
        json.dumps(metadata) if metadata else None,
    )
    return row["id"]


# ── Usage stats ────────────────────────────────────────────────

async def insert_usage(
    session_id: uuid.UUID | None,
    conversation_id: uuid.UUID | None,
    model_id: str,
    provider: str,
    tokens_prompt: int = 0,
    tokens_completion: int = 0,
    duration_ms: int | None = None,
    ip_address: str | None = None,
):
    ip = _safe_inet(ip_address)
    await pool().execute(
        """
        INSERT INTO duck.usage_stats
            (session_id, conversation_id, model_id, provider,
             tokens_prompt, tokens_completion, duration_ms, ip_address)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8::inet)
        """,
        session_id, conversation_id, model_id, provider,
        max(0, tokens_prompt or 0), max(0, tokens_completion or 0),
        duration_ms, ip,
    )


# ── History retrieval ──────────────────────────────────────────

async def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: int = 100,
) -> list[dict]:
    rows = await pool().fetch(
        """
        SELECT id, role, content, tokens_prompt, tokens_completion,
               model_id, provider, duration_ms, created_at
        FROM duck.messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        LIMIT $2
        """,
        conversation_id, limit,
    )
    return [dict(r) for r in rows]


async def get_session_conversations(
    session_id: uuid.UUID,
    limit: int = 20,
) -> list[dict]:
    rows = await pool().fetch(
        """
        SELECT id, title, model_id, provider, created_at, updated_at
        FROM duck.conversations
        WHERE session_id = $1 AND archived_at IS NULL
        ORDER BY updated_at DESC
        LIMIT $2
        """,
        session_id, limit,
    )
    return [dict(r) for r in rows]


# ── Analytics ──────────────────────────────────────────────────

async def get_model_usage_stats(
    since: datetime | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    clauses = ["1=1"]
    params: list = []
    idx = 1
    if since:
        clauses.append(f"created_at >= ${idx}")
        params.append(since)
        idx += 1
    if provider:
        clauses.append(f"provider = ${idx}")
        params.append(provider)
        idx += 1
    if model_id:
        clauses.append(f"model_id = ${idx}")
        params.append(model_id)
        idx += 1
    where = " AND ".join(clauses)
    rows = await pool().fetch(
        f"""
        SELECT model_id, provider,
               COUNT(*)               AS call_count,
               SUM(tokens_prompt)     AS total_prompt,
               SUM(tokens_completion) AS total_completion,
               SUM(total_tokens)      AS grand_total,
               AVG(duration_ms)       AS avg_duration_ms
        FROM duck.usage_stats
        WHERE {where}
        GROUP BY model_id, provider
        ORDER BY grand_total DESC NULLS LAST
        LIMIT ${idx}
        """,
        *params, limit,
    )
    return [dict(r) for r in rows]




# ── User accounts ──────────────────────────────────────────────



async def get_user_by_username(username: str) -> dict | None:
    row = await pool().fetchrow(
        "SELECT id, username, password_hash, security_question, security_answer, role, is_active, created_at FROM duck.users WHERE username = $1",
        username,
    )
    return dict(row) if row else None


async def set_user_token(username: str, token_hash: str):
    await pool().execute(
        "UPDATE duck.users SET token_hash = $1 WHERE username = $2",
        token_hash, username,
    )


async def get_user_token_hash(username: str) -> str | None:
    row = await pool().fetchrow(
        "SELECT token_hash FROM duck.users WHERE username = $1", username,
    )
    return row["token_hash"] if row else None


async def count_users() -> int:
    row = await pool().fetchrow("SELECT COUNT(*) AS cnt FROM duck.users")
    return row["cnt"] if row else 0


async def create_user(username: str, password_hash: str, security_question: str, security_answer_hash: str) -> dict | None:
    row = await pool().fetchrow(
        """INSERT INTO duck.users (username, password_hash, security_question, security_answer)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (username) DO NOTHING
           RETURNING id, username, created_at""",
        username, password_hash, security_question, security_answer_hash,
    )
    return dict(row) if row else None


async def get_user_security(username: str) -> dict | None:
    row = await pool().fetchrow(
        "SELECT security_question, security_answer FROM duck.users WHERE username = $1",
        username,
    )
    return dict(row) if row else None


async def update_user_password(username: str, password_hash: str):
    # Also invalidate all existing tokens
    await pool().execute(
        "UPDATE duck.users SET password_hash = $1, token_hash = '' WHERE username = $2",
        password_hash, username,
    )


async def get_user_by_token_hash(token_hash: str) -> dict | None:
    row = await pool().fetchrow(
        "SELECT id, username, role, is_active FROM duck.users WHERE token_hash = $1",
        token_hash,
    )
    return dict(row) if row else None


# ── Admin helpers ───────────────────────────────────────────────

async def list_users(limit: int = 100, offset: int = 0) -> list[dict]:
    rows = await pool().fetch(
        """
        SELECT id, username, role, is_active, created_at
        FROM duck.users
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit, offset,
    )
    return [dict(r) for r in rows]


async def count_users_total() -> int:
    row = await pool().fetchrow("SELECT COUNT(*) AS cnt FROM duck.users")
    return row["cnt"] if row else 0


async def update_user_role(user_id: str, role: str) -> bool:
    if role not in ("user", "admin"):
        raise ValueError(f"invalid role: {role}")
    result = await pool().execute(
        "UPDATE duck.users SET role = $1 WHERE id = $2::uuid",
        role, user_id,
    )
    return result != "UPDATE 0"


async def set_user_active(user_id: str, is_active: bool) -> bool:
    result = await pool().execute(
        "UPDATE duck.users SET is_active = $1 WHERE id = $2::uuid",
        is_active, user_id,
    )
    return result != "UPDATE 0"


async def get_admin_stats() -> dict:
    """Return aggregate counts for the admin dashboard."""
    rows = await pool().fetch("""
        SELECT
            (SELECT COUNT(*) FROM duck.users) AS total_users,
            (SELECT COUNT(*) FROM duck.conversations) AS total_conversations,
            (SELECT COUNT(*) FROM duck.messages) AS total_messages,
            (SELECT COUNT(*) FROM duck.usage_stats) AS total_usage_records,
            COALESCE((SELECT SUM(tokens_prompt + tokens_completion) FROM duck.usage_stats), 0) AS total_tokens
    """)
    return dict(rows[0]) if rows else {}


async def get_recent_usage(limit: int = 20) -> list[dict]:
    rows = await pool().fetch(
        """
        SELECT id, model_id, provider, tokens_prompt, tokens_completion,
               duration_ms, created_at
        FROM duck.usage_stats
        ORDER BY created_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]
