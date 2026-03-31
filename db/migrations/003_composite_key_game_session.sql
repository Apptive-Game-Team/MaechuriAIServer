-- Migration: Change game_session to use composite primary key
-- Purpose: Allow one user to play multiple scenarios simultaneously
-- Changes:
--   - session_id: VARCHAR(36) -> VARCHAR(255) (to support user identifiers like 'user1')
--   - PRIMARY KEY: session_id -> (session_id, scenario_id)
--   - Remove scenario_id index (no longer needed as it's part of primary key)

-- Step 1: Drop existing table (if you have data, export it first)
DROP TABLE IF EXISTS game_session CASCADE;

-- Step 2: Recreate table with composite primary key
CREATE TABLE game_session (
    session_id VARCHAR(255) NOT NULL,
    scenario_id INT NOT NULL REFERENCES scenario(scenario_id) ON DELETE CASCADE,

    -- Game State
    current_pressure INT DEFAULT 0,
    suspect_pressures JSONB DEFAULT '{}'::jsonb,
    evidence_seen_ids JSONB DEFAULT '[]'::jsonb,

    -- Progress Tracking
    suspect_interactions JSONB DEFAULT '{}'::jsonb,
    clue_interactions JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- Composite Primary Key
    PRIMARY KEY (session_id, scenario_id)
);

-- Comments
COMMENT ON TABLE game_session IS 'Game session tracking player progress and state. Uses composite key (session_id, scenario_id) to allow one user to play multiple scenarios.';
COMMENT ON COLUMN game_session.session_id IS 'User identifier (e.g., user ID from external auth system)';
COMMENT ON COLUMN game_session.scenario_id IS 'Scenario being played';
COMMENT ON COLUMN game_session.suspect_interactions IS 'Track interactions per suspect: {suspect_id: interaction_count}';
COMMENT ON COLUMN game_session.clue_interactions IS 'Track clue analysis: {clue_id: analyzed_count}';
COMMENT ON COLUMN game_session.suspect_pressures IS 'Per-suspect pressure: {suspect_id: pressure_value}';
