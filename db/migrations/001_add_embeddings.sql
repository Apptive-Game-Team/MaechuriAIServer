-- Migration: Add embedding columns for RAG support
-- Requires: pgvector extension (CREATE EXTENSION IF NOT EXISTS vector;)

-- 1. Enable pgvector extension (should already be installed)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Add embedding columns to suspect_timeline table
-- For semantic search over timeline entries (time, location, activity)
ALTER TABLE suspect_timeline
ADD COLUMN IF NOT EXISTS embedding vector(1024);

-- 3. Add embedding columns to suspect_secret table
-- For semantic search over secrets
ALTER TABLE suspect_secret
ADD COLUMN IF NOT EXISTS embedding vector(1024);

-- 4. Add embedding columns to clue table
-- For semantic search over clue descriptions and logic explanations
ALTER TABLE clue
ADD COLUMN IF NOT EXISTS description_embedding vector(1024),
ADD COLUMN IF NOT EXISTS logic_embedding vector(1024);

-- 5. Create chat_message_embedding table
-- For semantic search over conversation history
CREATE TABLE IF NOT EXISTS chat_message_embedding (
    id SERIAL PRIMARY KEY,
    scenario_id INT NOT NULL REFERENCES scenario(scenario_id) ON DELETE CASCADE,
    session_id VARCHAR(36) NOT NULL,
    suspect_id INT,
    clue_id INT,
    message_index INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. Create indexes for efficient vector search (HNSW for approximate nearest neighbor)
-- HNSW is faster for search, IVFFlat is faster for building

-- Index for suspect_timeline embeddings
CREATE INDEX IF NOT EXISTS idx_suspect_timeline_embedding
ON suspect_timeline USING hnsw (embedding vector_cosine_ops);

-- Index for suspect_secret embeddings
CREATE INDEX IF NOT EXISTS idx_suspect_secret_embedding
ON suspect_secret USING hnsw (embedding vector_cosine_ops);

-- Index for clue description embeddings
CREATE INDEX IF NOT EXISTS idx_clue_description_embedding
ON clue USING hnsw (description_embedding vector_cosine_ops);

-- Index for clue logic embeddings
CREATE INDEX IF NOT EXISTS idx_clue_logic_embedding
ON clue USING hnsw (logic_embedding vector_cosine_ops);

-- Index for chat_message_embedding
CREATE INDEX IF NOT EXISTS idx_chat_message_embedding
ON chat_message_embedding USING hnsw (embedding vector_cosine_ops);

-- Additional B-tree indexes for filtering
CREATE INDEX IF NOT EXISTS idx_chat_message_scenario_session
ON chat_message_embedding (scenario_id, session_id);

CREATE INDEX IF NOT EXISTS idx_chat_message_suspect
ON chat_message_embedding (scenario_id, suspect_id) WHERE suspect_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chat_message_clue
ON chat_message_embedding (scenario_id, clue_id) WHERE clue_id IS NOT NULL;

-- 7. Add embedding column to suspect table for profile embedding (name, role, description)
ALTER TABLE suspect
ADD COLUMN IF NOT EXISTS profile_embedding vector(1024);

CREATE INDEX IF NOT EXISTS idx_suspect_profile_embedding
ON suspect USING hnsw (profile_embedding vector_cosine_ops);
