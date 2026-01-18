-- ============================================================
-- Maechuri AI Server - PostgreSQL Schema
-- Primary Key: (scenario_id, local_id) 복합키 방식
-- ID 체계: 모든 테이블에서 1, 2, 3... 단순 시퀀스 사용
-- ============================================================

-- ============================================================
-- SCENARIO (루트 테이블)
-- ============================================================
CREATE TABLE scenario (
    scenario_id         SERIAL PRIMARY KEY,

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
    incident_location   VARCHAR(100) NOT NULL,
    primary_object      VARCHAR(100) NOT NULL,

    -- Ground Truth
    crime_time_start    TIME NOT NULL,
    crime_time_end      TIME NOT NULL,
    crime_location      VARCHAR(100) NOT NULL,
    crime_method        TEXT NOT NULL,

    -- Constraints
    no_supernatural     BOOLEAN NOT NULL DEFAULT TRUE,
    no_time_travel      BOOLEAN NOT NULL DEFAULT TRUE,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- LOCATION (시나리오 내 장소 목록)
-- ============================================================
CREATE TABLE location (
    scenario_id         INT NOT NULL,
    location_id         INT NOT NULL,
    name                VARCHAR(100) NOT NULL,

    PRIMARY KEY (scenario_id, location_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- VISIBILITY_RULE
-- ============================================================
CREATE TABLE visibility_rule (
    scenario_id         INT NOT NULL,
    rule_id             INT NOT NULL,
    from_location       VARCHAR(100) NOT NULL,
    can_see             JSONB NOT NULL DEFAULT '[]',
    cannot_see          JSONB NOT NULL DEFAULT '[]',
    evidence_type       VARCHAR(50),

    PRIMARY KEY (scenario_id, rule_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- ACCESS_RULE
-- ============================================================
CREATE TABLE access_rule (
    scenario_id         INT NOT NULL,
    rule_id             INT NOT NULL,
    location            VARCHAR(100) NOT NULL,
    requires            VARCHAR(100) NOT NULL,

    PRIMARY KEY (scenario_id, rule_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- REQUIRED_EVIDENCE (정답 판정용 필수 증거)
-- ============================================================
CREATE TABLE required_evidence (
    scenario_id         INT NOT NULL,
    evidence_id         INT NOT NULL,
    type                VARCHAR(50) NOT NULL,
    min_count           INT NOT NULL CHECK (min_count >= 1),

    PRIMARY KEY (scenario_id, evidence_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- SUSPECT (용의자)
-- ============================================================
CREATE TABLE suspect (
    scenario_id         INT NOT NULL,
    suspect_id          INT NOT NULL,

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

    -- 자백 트리거 증거 IDs (local clue_id 배열)
    critical_evidence_ids JSONB NOT NULL DEFAULT '[]',

    PRIMARY KEY (scenario_id, suspect_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- SUSPECT_TIMELINE (용의자 타임라인)
-- ============================================================
CREATE TABLE suspect_timeline (
    scenario_id         INT NOT NULL,
    suspect_id          INT NOT NULL,
    timeline_id         INT NOT NULL,

    time_range          VARCHAR(50) NOT NULL,
    location            VARCHAR(100) NOT NULL,
    activity            TEXT NOT NULL,
    can_prove           BOOLEAN NOT NULL DEFAULT FALSE,
    witness             VARCHAR(100),

    PRIMARY KEY (scenario_id, suspect_id, timeline_id),
    FOREIGN KEY (scenario_id, suspect_id) REFERENCES suspect(scenario_id, suspect_id) ON DELETE CASCADE
);

-- ============================================================
-- SUSPECT_SECRET (용의자 비밀 - 압박 단계별)
-- ============================================================
CREATE TABLE suspect_secret (
    scenario_id         INT NOT NULL,
    suspect_id          INT NOT NULL,
    secret_id           INT NOT NULL,

    threshold           INT NOT NULL CHECK (threshold >= 0 AND threshold <= 100),
    content             TEXT NOT NULL,
    trigger_evidence_ids JSONB NOT NULL DEFAULT '[]',

    PRIMARY KEY (scenario_id, suspect_id, secret_id),
    FOREIGN KEY (scenario_id, suspect_id) REFERENCES suspect(scenario_id, suspect_id) ON DELETE CASCADE
);

-- ============================================================
-- CLUE (단서)
-- ============================================================
CREATE TABLE clue (
    scenario_id         INT NOT NULL,
    clue_id             INT NOT NULL,

    name                VARCHAR(100) NOT NULL,
    found_at            VARCHAR(100) NOT NULL,
    description         TEXT NOT NULL,
    related_suspect_ids JSONB NOT NULL DEFAULT '[]',
    logic_explanation   TEXT NOT NULL,
    decoded_answer      TEXT,  -- 증거 분석 시 형사가 알려줄 해독된 답 (nullable)
    is_red_herring      BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY (scenario_id, clue_id),
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE
);

-- ============================================================
-- INDEXES (조회 성능)
-- ============================================================
CREATE INDEX idx_suspect_culprit ON suspect(scenario_id, is_culprit);
CREATE INDEX idx_clue_location ON clue(scenario_id, found_at);
CREATE INDEX idx_clue_red_herring ON clue(scenario_id, is_red_herring);
CREATE INDEX idx_secret_threshold ON suspect_secret(scenario_id, suspect_id, threshold);
