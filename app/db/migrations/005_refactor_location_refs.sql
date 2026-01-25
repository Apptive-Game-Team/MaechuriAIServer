-- Migration: Refactor location references to use ID instead of Name
-- Includes data reset and sequence reset as requested.

-- 1. Reset Data and Sequence
TRUNCATE TABLE scenario CASCADE;
ALTER SEQUENCE scenario_scenario_id_seq RESTART WITH 1;

-- 2. Modify Tables to use location_id

-- ACCESS_RULE
-- Drop old column and add new FK column
ALTER TABLE access_rule DROP COLUMN location;
ALTER TABLE access_rule ADD COLUMN location_id BIGINT NOT NULL;
ALTER TABLE access_rule ADD CONSTRAINT access_rule_location_fk
    FOREIGN KEY (scenario_id, location_id) REFERENCES location(scenario_id, location_id) ON DELETE CASCADE;

-- VISIBILITY_RULE
-- Drop old column and add new FK column
ALTER TABLE visibility_rule DROP COLUMN from_location;
ALTER TABLE visibility_rule ADD COLUMN from_location_id BIGINT NOT NULL;
ALTER TABLE visibility_rule ADD CONSTRAINT visibility_rule_location_fk
    FOREIGN KEY (scenario_id, from_location_id) REFERENCES location(scenario_id, location_id) ON DELETE CASCADE;
-- Note: can_see and cannot_see JSONB columns will now be expected to store lists of location IDs (integers).

-- SUSPECT_TIMELINE
ALTER TABLE suspect_timeline DROP COLUMN location;
ALTER TABLE suspect_timeline ADD COLUMN location_id BIGINT NOT NULL;
ALTER TABLE suspect_timeline ADD CONSTRAINT suspect_timeline_location_fk
    FOREIGN KEY (scenario_id, location_id) REFERENCES location(scenario_id, location_id) ON DELETE CASCADE;

-- CLUE
ALTER TABLE clue DROP COLUMN found_at;
ALTER TABLE clue ADD COLUMN location_id BIGINT NOT NULL;
ALTER TABLE clue ADD CONSTRAINT clue_location_fk
    FOREIGN KEY (scenario_id, location_id) REFERENCES location(scenario_id, location_id) ON DELETE CASCADE;
