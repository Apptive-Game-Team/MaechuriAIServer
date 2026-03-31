-- Migration 021: Add asset prompt/embedding columns and metadata
-- Asset 테이블에 prompt 기반 임베딩 및 추가 메타 컬럼을 반영

-- Ensure pgvector extension exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Rename legacy column if present
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'asset' AND column_name = 'meta_file_url'
    ) THEN
        ALTER TABLE asset RENAME COLUMN meta_file_url TO final_url;
    END IF;
END $$;

-- Allow NULL for async generation
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'asset' AND column_name = 'final_url'
    ) THEN
        ALTER TABLE asset ALTER COLUMN final_url DROP NOT NULL;
    END IF;
END $$;

-- Add new columns for prompts, urls, status, timestamps, and embedding
ALTER TABLE IF EXISTS asset
    ADD COLUMN IF NOT EXISTS prompt TEXT,
    ADD COLUMN IF NOT EXISTS raw_url VARCHAR(512),
    ADD COLUMN IF NOT EXISTS resized_url VARCHAR(512),
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'COMPLETED',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS embedding vector(1024);

-- Vector index for semantic search
CREATE INDEX IF NOT EXISTS idx_asset_embedding
ON asset USING hnsw (embedding vector_cosine_ops);
