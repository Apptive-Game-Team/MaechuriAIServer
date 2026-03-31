-- ============================================================
-- Migration 010: Create map table and add position columns
-- ============================================================

-- Create map table for storing rooms and corridors with positions
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

-- Index for efficient lookup
CREATE INDEX idx_map_scenario ON map(scenario_id);
CREATE INDEX idx_map_type ON map(scenario_id, type);

-- Add position columns to suspect table
ALTER TABLE suspect ADD COLUMN x SMALLINT;
ALTER TABLE suspect ADD COLUMN y SMALLINT;

-- Add position columns to clue table
ALTER TABLE clue ADD COLUMN x SMALLINT;
ALTER TABLE clue ADD COLUMN y SMALLINT;

-- Comments
COMMENT ON TABLE map IS 'Map elements (rooms and corridors) with calculated positions';
COMMENT ON COLUMN map.type IS 'Element type: room or corridor';
COMMENT ON COLUMN map.x IS 'Bottom-left X coordinate';
COMMENT ON COLUMN map.y IS 'Bottom-left Y coordinate';
COMMENT ON COLUMN map.extra_data IS 'Additional data: mood for rooms, connections for corridors';
COMMENT ON COLUMN suspect.x IS 'X position on map (within room)';
COMMENT ON COLUMN suspect.y IS 'Y position on map (within room)';
COMMENT ON COLUMN clue.x IS 'X position on map (within room)';
COMMENT ON COLUMN clue.y IS 'Y position on map (within room)';
