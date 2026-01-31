-- Migration: Create scenario_context table for RAG
-- 조력자(형사)가 참조하는 공개 가능한 정보만 저장
-- ground_truth, suspect 민감 정보는 절대 저장하지 않음

CREATE TABLE scenario_context (
    scenario_id         BIGINT NOT NULL,
    context_id          BIGINT NOT NULL,

    -- 허용 타입 제한: incident, location, world만
    type                VARCHAR(50) NOT NULL
                        CHECK (type IN ('incident', 'location', 'world')),
    content             TEXT NOT NULL,
    extra_data          JSONB DEFAULT '{}',
    embedding           vector(1024),

    PRIMARY KEY (scenario_id, context_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

CREATE INDEX idx_scenario_context_embedding
ON scenario_context USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_scenario_context_type
ON scenario_context (scenario_id, type);

-- gamesession table 변경

-- 1. 신규 컬럼 생성 (JSONB)
ALTER TABLE game_session ADD COLUMN clue_seen_ids JSONB;

-- 2. 데이터 복제
-- (기존 컬럼이 만약 VARCHAR였다면 USING evidence_seen_ids::jsonb 처럼 형변환이 필요할 수 있습니다)
UPDATE  game_session SET clue_seen_ids = evidence_seen_ids;

-- 3. 구 컬럼 삭제
ALTER TABLE game_session DROP COLUMN evidence_seen_ids;