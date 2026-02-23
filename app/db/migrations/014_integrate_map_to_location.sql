-- ============================================================
-- Migration 014: Integrate map table into location table
-- Rooms and corridors are now stored as location rows.
-- ============================================================

-- Add geometry and type columns to location
ALTER TABLE location
    ADD COLUMN type    VARCHAR(20) NOT NULL DEFAULT 'room'
                       CHECK (type IN ('room', 'corridor')),
    ADD COLUMN x       SMALLINT,
    ADD COLUMN y       SMALLINT,
    ADD COLUMN width   SMALLINT,
    ADD COLUMN height  SMALLINT;

-- ============================================================
-- Transfer room geometry: match map rooms to locations by name
-- ============================================================
UPDATE location l
SET
    type   = 'room',
    x      = m.x,
    y      = m.y,
    width  = m.width,
    height = m.height
FROM map m
WHERE l.scenario_id = m.scenario_id
  AND l.name        = m.name
  AND m.type        = 'room';

-- ============================================================
-- Transfer corridors: insert as new location rows
-- location_id = max(existing location_id per scenario) + row offset
-- ============================================================
WITH corridors AS (
    SELECT
        m.scenario_id,
        m.name,
        m.x,
        m.y,
        m.width,
        m.height,
        MAX(l.location_id) OVER (PARTITION BY m.scenario_id) AS max_loc_id,
        ROW_NUMBER()        OVER (PARTITION BY m.scenario_id ORDER BY m.map_id) AS rn
    FROM map m
    JOIN location l ON l.scenario_id = m.scenario_id
    WHERE m.type = 'corridor'
)
INSERT INTO location (scenario_id, location_id, name, type, x, y, width, height)
SELECT
    scenario_id,
    max_loc_id + rn,
    name,
    'corridor',
    x,
    y,
    width,
    height
FROM corridors;

-- Add index for type filtering
CREATE INDEX idx_location_type ON location(scenario_id, type);

-- Drop map table
DROP TABLE IF EXISTS map;
