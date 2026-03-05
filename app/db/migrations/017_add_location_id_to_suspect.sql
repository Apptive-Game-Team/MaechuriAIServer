ALTER TABLE suspect ADD COLUMN IF NOT EXISTS location_id BIGINT;
ALTER TABLE suspect ADD CONSTRAINT fk_suspect_location
    FOREIGN KEY (scenario_id, location_id)
    REFERENCES location(scenario_id, location_id) ON DELETE CASCADE;


ALTER TABLE suspect
    ADD COLUMN IF NOT EXISTS assets_url TEXT;

ALTER TABLE clue
    ADD COLUMN IF NOT EXISTS assets_url TEXT;