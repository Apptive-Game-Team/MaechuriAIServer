-- Migration: Refactor Scenario location columns to use IDs (Foreign Keys)
-- 1. Rename old text columns (to keep data temporarily or drop later)
-- 2. Add new BIGINT columns
-- 3. Add Foreign Key constraints

-- Note: We are dropping the old columns directly assuming development environment.
-- If production data migration is needed, we would need UPDATE statements using mapping.

ALTER TABLE scenario DROP COLUMN incident_location;
ALTER TABLE scenario DROP COLUMN crime_location;

ALTER TABLE scenario ADD COLUMN incident_location_id BIGINT;
ALTER TABLE scenario ADD COLUMN crime_location_id BIGINT;

-- Add Foreign Keys
-- Constraints are deferred or we ensure locations exist first? 
-- Usually locations are inserted AFTER scenario, but FK requires location to exist.
-- Circular dependency issue:
-- Scenario -> has Locations -> references Scenario (FK)
-- Scenario -> references Location (incident_loc_id)
-- To resolve this:
-- 1. Insert Scenario with NULL location_ids
-- 2. Insert Locations
-- 3. Update Scenario with location_ids
-- OR: Make columns nullable initially.

-- Let's make them nullable to handle the circular insertion dependency easily.
ALTER TABLE scenario ALTER COLUMN incident_location_id DROP NOT NULL;
ALTER TABLE scenario ALTER COLUMN crime_location_id DROP NOT NULL;

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
