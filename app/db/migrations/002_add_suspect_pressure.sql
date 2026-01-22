-- Migration: Create game_session table (including suspect_pressures)
-- Purpose: Manage player game state and progress

CREATE TABLE IF NOT EXISTS game_session (
    session_id VARCHAR(36) PRIMARY KEY,
    scenario_id INT NOT NULL REFERENCES scenario(scenario_id) ON DELETE CASCADE,
    
    -- Game State
    current_pressure INT DEFAULT 0,
    suspect_pressures JSONB DEFAULT '{}'::jsonb, -- New column included in creation
    evidence_seen_ids JSONB DEFAULT '[]'::jsonb,
    
    -- Progress Tracking
    suspect_interactions JSONB DEFAULT '{}'::jsonb,
    clue_interactions JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_game_session_scenario_id ON game_session(scenario_id);

-- Comments
COMMENT ON TABLE game_session IS 'Game session tracking player progress and state.';
COMMENT ON COLUMN game_session.suspect_interactions IS 'Track interactions per suspect: {suspect_id: interaction_count}';
COMMENT ON COLUMN game_session.clue_interactions IS 'Track clue analysis: {clue_id: analyzed_count}';
COMMENT ON COLUMN game_session.suspect_pressures IS 'Per-suspect pressure: {suspect_id: pressure_value}';