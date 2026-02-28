-- ============================================================
-- Migration 015: Add NOT NULL constraints to coordinate fields
-- and delete scenarios with null coordinate data.
-- ============================================================

-- 1. Identify all scenarios that have null coordinate values in location, suspect, or clue tables.
WITH scenarios_to_delete AS (
    -- Scenarios with nulls in the location table
    SELECT scenario_id FROM location WHERE x IS NULL OR y IS NULL OR width IS NULL OR height IS NULL
    UNION
    -- Scenarios with nulls in the suspect table
    SELECT scenario_id FROM suspect WHERE x IS NULL OR y IS NULL
    UNION
    -- Scenarios with nulls in the clue table
    SELECT scenario_id FROM clue WHERE x IS NULL OR y IS NULL
)
-- 2. Delete the identified scenarios.
-- Due to ON DELETE CASCADE, all related data in other tables will be deleted automatically.
DELETE FROM scenario
WHERE scenario_id IN (SELECT DISTINCT scenario_id FROM scenarios_to_delete);


-- 3. Add NOT NULL constraints to the coordinate columns now that all nulls are removed.

-- location table
ALTER TABLE location
    ALTER COLUMN x SET NOT NULL,
    ALTER COLUMN y SET NOT NULL,
    ALTER COLUMN width SET NOT NULL,
    ALTER COLUMN height SET NOT NULL;

-- suspect table
ALTER TABLE suspect
    ALTER COLUMN x SET NOT NULL,
    ALTER COLUMN y SET NOT NULL;

-- clue table
ALTER TABLE clue
    ALTER COLUMN x SET NOT NULL,
    ALTER COLUMN y SET NOT NULL;

-- [Verification Query - Optional]
-- You can run these checks after migration to ensure no nulls exist.
-- SELECT COUNT(*) FROM location WHERE x IS NULL OR y IS NULL OR width IS NULL OR height IS NULL;
-- SELECT COUNT(*) FROM suspect WHERE x IS NULL OR y IS NULL;
-- SELECT COUNT(*) FROM clue WHERE x IS NULL OR y IS NULL;
