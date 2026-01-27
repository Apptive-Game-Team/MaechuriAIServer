DROP TABLE IF EXISTS suspect_timeline;
DROP TABLE IF EXISTS suspect_secret;

CREATE TABLE IF NOT EXISTS fact (
    scenario_id BIGINT NOT NULL REFERENCES scenario(scenario_id) ON DELETE CASCADE,
    suspect_id BIGINT NOT NULL,
    fact_id BIGINT NOT NULL,

    threshold INT NOT NULL DEFAULT 0,

    type VARCHAR(50) NOT NULL, -- e.g., "secret", "timeline"
    content JSONB NOT NULL,
    embedding vector(1024),

    FOREIGN KEY (scenario_id, suspect_id)
        REFERENCES suspect(scenario_id, suspect_id)
        ON DELETE CASCADE,
    PRIMARY KEY (scenario_id, fact_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_embedding
ON fact USING hnsw (embedding vector_cosine_ops);

ALTER TABLE clue DROP COLUMN IF EXISTS related_suspect_ids;
ALTER TABLE clue ADD COLUMN related_fact_ids JSONB;