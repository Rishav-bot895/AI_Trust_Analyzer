-- AI Trust Analyzer production schema for Supabase PostgreSQL + pgvector

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY,
    prompt TEXT,
    response TEXT,
    model_name VARCHAR(128),
    include_comparison BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(32) NOT NULL,
    trust_score DOUBLE PRECISION,
    hallucination_risk VARCHAR(32),
    critique TEXT,
    verdict TEXT,
    timeline TEXT,
    error TEXT,
    user_id TEXT,
    guest_session_id TEXT,
    is_guest BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY,
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    status VARCHAR(32) NOT NULL,
    claim_index INTEGER NOT NULL DEFAULT 0,
    source_span TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY,
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    snippet TEXT NOT NULL,
    source_url TEXT,
    source_title TEXT,
    relevance_score DOUBLE PRECISION NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    polarity VARCHAR(16),
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_embeddings (
    id TEXT PRIMARY KEY,
    evidence_id TEXT,
    snippet TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    user_id TEXT,
    guest_session_id TEXT,
    is_guest BOOLEAN NOT NULL DEFAULT FALSE,
    embedding vector(384) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses (status);
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses (user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_guest_session_id ON analyses (guest_session_id);
CREATE INDEX IF NOT EXISTS idx_analyses_is_guest ON analyses (is_guest);
CREATE INDEX IF NOT EXISTS idx_claims_analysis_id ON claims (analysis_id);
CREATE INDEX IF NOT EXISTS idx_evidence_claim_id ON evidence (claim_id);
CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_embedding
ON evidence_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_user_id ON evidence_embeddings (user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_guest_session_id ON evidence_embeddings (guest_session_id);
CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_is_guest ON evidence_embeddings (is_guest);

COMMIT;
