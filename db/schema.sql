-- ============================================================
-- Maechuri AI Server - PostgreSQL Schema
-- Primary Key: (scenario_id, local_id) 복합키 방식
-- ID 체계: 모든 테이블에서 1, 2, 3... 단순 시퀀스 사용
-- ============================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- SCENARIO (루트 테이블)
-- ============================================================
CREATE TABLE scenario (
    scenario_id         BIGSERIAL PRIMARY KEY,

    -- Meta
    difficulty          VARCHAR(10) NOT NULL CHECK (difficulty IN ('easy', 'mid', 'hard')),
    theme               VARCHAR(100) NOT NULL,
    tone                VARCHAR(100) NOT NULL,
    language            VARCHAR(10) NOT NULL DEFAULT 'ko',

    -- Incident
    incident_type       VARCHAR(100) NOT NULL,
    incident_summary    TEXT NOT NULL,
    incident_time_start TIME NOT NULL,
    incident_time_end   TIME NOT NULL,
    incident_location_id BIGINT,  -- FK to location (nullable for circular dep)
    primary_object      VARCHAR(100) NOT NULL,

    -- Ground Truth
    crime_time_start    TIME NOT NULL,
    crime_time_end      TIME NOT NULL,
    crime_location_id   BIGINT,  -- FK to location (nullable for circular dep)
    crime_method        TEXT NOT NULL,

    -- Constraints
    no_supernatural     BOOLEAN NOT NULL DEFAULT TRUE,
    no_time_travel      BOOLEAN NOT NULL DEFAULT TRUE,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- LOCATION (시나리오 내 장소 목록)
-- visibility_rule, access_rule 통합
-- ============================================================
CREATE TABLE location (
    scenario_id         BIGINT NOT NULL,
    location_id         BIGINT NOT NULL,
    name                VARCHAR(100) NOT NULL,
    can_see             JSONB DEFAULT '[]',      -- List of location_ids visible from here
    cannot_see          JSONB DEFAULT '[]',      -- List of location_ids not visible from here
    access_requires     VARCHAR(100),            -- Access requirement (e.g., key name)

    PRIMARY KEY (scenario_id, location_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- Add FKs for scenario location references (after location table exists)
ALTER TABLE scenario
    ADD CONSTRAINT fk_scenario_incident_location
    FOREIGN KEY (scenario_id, incident_location_id)
    REFERENCES location(scenario_id, location_id)
    ON DELETE SET NULL;

ALTER TABLE scenario
    ADD CONSTRAINT fk_scenario_crime_location
    FOREIGN KEY (scenario_id, crime_location_id)
    REFERENCES location(scenario_id, location_id)
    ON DELETE SET NULL;

-- ============================================================
-- MAP (맵 요소 - 방, 복도)
-- ============================================================
CREATE TABLE map (
    scenario_id         BIGINT NOT NULL,
    map_id              BIGINT NOT NULL,

    type                VARCHAR(20) NOT NULL CHECK (type IN ('room', 'corridor')),
    name                VARCHAR(100) NOT NULL,

    -- Position (bottom-left origin)
    x                   SMALLINT NOT NULL,
    y                   SMALLINT NOT NULL,

    -- Dimensions
    width               SMALLINT NOT NULL,
    height              SMALLINT NOT NULL,

    -- Additional data (mood for rooms, connections for corridors)
    extra_data          JSONB DEFAULT '{}',

    PRIMARY KEY (scenario_id, map_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- SUSPECT (용의자)
-- ============================================================
CREATE TABLE suspect (
    scenario_id         BIGINT NOT NULL,
    suspect_id          BIGINT NOT NULL,

    name                VARCHAR(100) NOT NULL,
    role                VARCHAR(100) NOT NULL,
    age                 INT NOT NULL,
    gender              VARCHAR(20) NOT NULL,
    description         TEXT NOT NULL,

    is_culprit          BOOLEAN NOT NULL DEFAULT FALSE,
    motive              TEXT,
    alibi_summary       TEXT NOT NULL,

    -- Personality
    speech_style        VARCHAR(100) NOT NULL,
    emotional_tendency  VARCHAR(100) NOT NULL,
    lying_pattern       VARCHAR(50) NOT NULL,

    -- 자백 트리거 단서 IDs (local clue_id 배열)
    critical_clue_ids   JSONB NOT NULL DEFAULT '[]',

    -- Map position (within room)
    x                   SMALLINT,
    y                   SMALLINT,

    -- Embedding for RAG
    profile_embedding   vector(1024),

    PRIMARY KEY (scenario_id, suspect_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- FACT (용의자 타임라인 + 비밀 통합)
-- ============================================================
CREATE TABLE fact (
    scenario_id         BIGINT NOT NULL,
    suspect_id          BIGINT NOT NULL DEFAULT 0,  -- 0 = scenario context, >0 = suspect fact
    fact_id             BIGINT NOT NULL,

    threshold           INT NOT NULL DEFAULT 0,
    type                VARCHAR(50) NOT NULL
                        CHECK (type IN ('secret', 'timeline', 'incident', 'location', 'world')),
    content             JSONB NOT NULL,
    embedding           vector(1024),

    PRIMARY KEY (scenario_id, fact_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- CLUE (단서)
-- ============================================================
CREATE TABLE clue (
    scenario_id         BIGINT NOT NULL,
    clue_id             BIGINT NOT NULL,

    name                VARCHAR(100) NOT NULL,
    location_id         BIGINT NOT NULL,  -- FK to location
    description         TEXT NOT NULL,
    related_suspect_ids JSONB DEFAULT '[]',
    logic_explanation   TEXT NOT NULL,
    decoded_answer      TEXT,  -- 단서 분석 시 형사가 알려줄 해독된 답 (nullable)
    is_red_herring      BOOLEAN NOT NULL DEFAULT FALSE,

    -- Map position (within room)
    x                   SMALLINT,
    y                   SMALLINT,

    -- Embeddings for RAG
    description_embedding vector(1024),
    logic_embedding       vector(1024),

    PRIMARY KEY (scenario_id, clue_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_id, location_id) REFERENCES location(scenario_id, location_id) ON DELETE CASCADE
);

-- ============================================================
-- GAME_SESSION (게임 세션)
-- ============================================================
CREATE TABLE game_session (
    session_id          VARCHAR(255) NOT NULL,
    scenario_id         BIGINT NOT NULL,

    -- Game State
    current_pressure    INT DEFAULT 0,
    suspect_pressures   JSONB DEFAULT '{}'::jsonb,
    clue_seen_ids       JSONB DEFAULT '[]'::jsonb,

    -- Progress Tracking
    suspect_interactions JSONB DEFAULT '{}'::jsonb,
    clue_interactions    JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at          TIMESTAMP DEFAULT NOW(),
    last_activity_at    TIMESTAMP DEFAULT NOW(),
    completed_at        TIMESTAMP,

    PRIMARY KEY (session_id, scenario_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- CHAT_MESSAGE_EMBEDDING (대화 기록 임베딩)
-- ============================================================
CREATE TABLE chat_message_embedding (
    id                  SERIAL PRIMARY KEY,
    scenario_id         BIGINT NOT NULL,
    session_id          VARCHAR(36) NOT NULL,
    suspect_id          BIGINT,
    clue_id             BIGINT,
    message_index       INT NOT NULL,
    role                VARCHAR(20) NOT NULL,
    content             TEXT NOT NULL,
    embedding           vector(1024),
    created_at          TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Map indexes
CREATE INDEX idx_map_scenario ON map(scenario_id);
CREATE INDEX idx_map_type ON map(scenario_id, type);

-- Suspect indexes
CREATE INDEX idx_suspect_culprit ON suspect(scenario_id, is_culprit);
CREATE INDEX idx_suspect_profile_embedding ON suspect USING hnsw (profile_embedding vector_cosine_ops);

-- Fact indexes
CREATE INDEX idx_fact_embedding ON fact USING hnsw (embedding vector_cosine_ops);

-- Clue indexes
CREATE INDEX idx_clue_location ON clue(scenario_id, location_id);
CREATE INDEX idx_clue_red_herring ON clue(scenario_id, is_red_herring);
CREATE INDEX idx_clue_description_embedding ON clue USING hnsw (description_embedding vector_cosine_ops);
CREATE INDEX idx_clue_logic_embedding ON clue USING hnsw (logic_embedding vector_cosine_ops);

-- Game session indexes
CREATE INDEX idx_game_session_scenario_id ON game_session(scenario_id);

-- Chat message indexes
CREATE INDEX idx_chat_message_embedding ON chat_message_embedding USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_chat_message_scenario_session ON chat_message_embedding(scenario_id, session_id);
CREATE INDEX idx_chat_message_suspect ON chat_message_embedding(scenario_id, suspect_id) WHERE suspect_id IS NOT NULL;
CREATE INDEX idx_chat_message_clue ON chat_message_embedding(scenario_id, clue_id) WHERE clue_id IS NOT NULL;

-- ============================================================
-- COMMENTS
-- ============================================================
COMMENT ON TABLE game_session IS 'Game session tracking player progress and state.';
COMMENT ON COLUMN game_session.suspect_interactions IS 'Track interactions per suspect: {suspect_id: interaction_count}';
COMMENT ON COLUMN game_session.clue_interactions IS 'Track clue analysis: {clue_id: analyzed_count}';
COMMENT ON COLUMN game_session.suspect_pressures IS 'Per-suspect pressure: {suspect_id: pressure_value}';
