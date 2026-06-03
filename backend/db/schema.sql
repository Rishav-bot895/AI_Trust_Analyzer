-- AI Trust Analyzer production schema for Supabase PostgreSQL + pgvector.
-- This schema is intended for PostgreSQL 15+.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    guest_session_id TEXT,
    is_guest BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    CONSTRAINT ck_chat_sessions_owner_scope CHECK (
        (is_guest = TRUE AND guest_session_id IS NOT NULL AND user_id IS NULL)
        OR
        (is_guest = FALSE AND user_id IS NOT NULL AND guest_session_id IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    prompt TEXT,
    response TEXT,
    model_name VARCHAR(128),
    include_comparison BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(32) NOT NULL,
    trust_score DOUBLE PRECISION,
    hallucination_risk VARCHAR(32),
    critique TEXT,
    verdict TEXT,
    timeline JSONB NOT NULL DEFAULT '[]'::jsonb,
    error TEXT,
    user_id UUID,
    guest_session_id TEXT,
    is_guest BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT ck_analyses_status CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    CONSTRAINT ck_analyses_hallucination_risk CHECK (
        hallucination_risk IS NULL
        OR hallucination_risk IN ('LOW', 'MEDIUM', 'HIGH', 'UNKNOWN')
    ),
    CONSTRAINT ck_analyses_owner_scope CHECK (
        (is_guest = TRUE AND guest_session_id IS NOT NULL AND user_id IS NULL)
        OR
        (is_guest = FALSE AND user_id IS NOT NULL AND guest_session_id IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    status VARCHAR(32) NOT NULL,
    claim_index INTEGER NOT NULL DEFAULT 0,
    source_span TEXT,
    CONSTRAINT ck_claims_confidence_range CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT ck_claims_status CHECK (
        status IN ('SUPPORTED', 'PARTIALLY_SUPPORTED', 'CONTRADICTED', 'UNSUPPORTED', 'UNVERIFIABLE')
    )
);

CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    snippet TEXT NOT NULL,
    source_url TEXT,
    source_title TEXT,
    relevance_score DOUBLE PRECISION NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    polarity VARCHAR(16),
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_evidence_relevance_nonnegative CHECK (relevance_score >= 0.0),
    CONSTRAINT ck_evidence_source_type CHECK (source_type IN ('WEB_SEARCH', 'PGVECTOR')),
    CONSTRAINT ck_evidence_polarity CHECK (polarity IS NULL OR polarity IN ('FOR', 'AGAINST'))
);

CREATE TABLE IF NOT EXISTS evidence_embeddings (
    evidence_id UUID PRIMARY KEY REFERENCES evidence(id) ON DELETE CASCADE,
    snippet TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    user_id UUID,
    guest_session_id TEXT,
    is_guest BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding vector(384) NOT NULL,
    CONSTRAINT ck_evidence_embeddings_owner_scope CHECK (
        (is_guest = TRUE AND guest_session_id IS NOT NULL AND user_id IS NULL)
        OR
        (is_guest = FALSE AND user_id IS NOT NULL AND guest_session_id IS NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_chat_sessions_guest_session_id
ON chat_sessions (guest_session_id)
WHERE guest_session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_expires_at ON chat_sessions (expires_at);

CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses (status);
CREATE INDEX IF NOT EXISTS idx_analyses_chat_session_id ON analyses (chat_session_id);
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses (user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_guest_session_id ON analyses (guest_session_id);
CREATE INDEX IF NOT EXISTS idx_analyses_is_guest ON analyses (is_guest);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_claims_analysis_id ON claims (analysis_id);
CREATE INDEX IF NOT EXISTS idx_evidence_claim_id ON evidence (claim_id);

CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_user_id ON evidence_embeddings (user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_guest_session_id ON evidence_embeddings (guest_session_id);
CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_is_guest ON evidence_embeddings (is_guest);
CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_embedding
ON evidence_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMIT;
