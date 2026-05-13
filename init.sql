-- Duck Chat — PostgreSQL initialisation (idempotent)
-- This runs on first container start. Re-runs are safe (IF NOT EXISTS).

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

-- v1 stored cloud_key in plaintext. Drop it if present.
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
