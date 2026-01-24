-- Migration: Change all ID columns to BIGINT and ensure scenario_id uses BIGSERIAL behavior
-- This migration updates all primary keys, foreign keys, and ID columns from INT to BIGINT.

-- 1. Drop existing Foreign Key constraints to allow type changes
-- We use a DO block to dynamically find and drop constraints referencing 'scenario' and 'suspect'
-- to avoid errors with hardcoded names (though we recreate them with standard names later).
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT conname, conrelid::regclass
        FROM pg_constraint
        WHERE confrelid IN ('scenario'::regclass, 'suspect'::regclass)
        AND contype = 'f'
    LOOP
        EXECUTE 'ALTER TABLE ' || r.conrelid || ' DROP CONSTRAINT ' || r.conname;
    END LOOP;
END $$;

-- 2. Alter Table Columns to BIGINT and Rename

-- SCENARIO (Root table)
ALTER TABLE scenario ALTER COLUMN scenario_id TYPE BIGINT;
-- Ensure scenario_id behaves like BIGSERIAL (autoincrement)
-- (SERIAL already has a sequence, we just ensure it's BIGINT)
ALTER SEQUENCE IF EXISTS scenario_scenario_id_seq AS BIGINT;

-- RENAME TABLE required_evidence TO required_clue
ALTER TABLE IF EXISTS required_evidence RENAME TO required_clue;

-- LOCATION
ALTER TABLE location ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE location ALTER COLUMN location_id TYPE BIGINT;

-- VISIBILITY_RULE
ALTER TABLE visibility_rule ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE visibility_rule ALTER COLUMN rule_id TYPE BIGINT;
ALTER TABLE visibility_rule RENAME COLUMN evidence_type TO clue_type;

-- ACCESS_RULE
ALTER TABLE access_rule ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE access_rule ALTER COLUMN rule_id TYPE BIGINT;

-- REQUIRED_CLUE
ALTER TABLE required_clue ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE required_clue ALTER COLUMN evidence_id TYPE BIGINT;
ALTER TABLE required_clue RENAME COLUMN evidence_id TO clue_id;

-- SUSPECT
ALTER TABLE suspect ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE suspect ALTER COLUMN suspect_id TYPE BIGINT;
ALTER TABLE suspect RENAME COLUMN critical_evidence_ids TO critical_clue_ids;

-- SUSPECT_TIMELINE
ALTER TABLE suspect_timeline ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE suspect_timeline ALTER COLUMN suspect_id TYPE BIGINT;
ALTER TABLE suspect_timeline ALTER COLUMN timeline_id TYPE BIGINT;

-- SUSPECT_SECRET
ALTER TABLE suspect_secret ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE suspect_secret ALTER COLUMN suspect_id TYPE BIGINT;
ALTER TABLE suspect_secret ALTER COLUMN secret_id TYPE BIGINT;
ALTER TABLE suspect_secret RENAME COLUMN trigger_evidence_ids TO trigger_clue_ids;

-- CLUE
ALTER TABLE clue ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE clue ALTER COLUMN clue_id TYPE BIGINT;

-- GAME_SESSION
ALTER TABLE game_session ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE game_session RENAME COLUMN evidence_seen_ids TO clue_seen_ids;

-- CHAT_MESSAGE_EMBEDDING
-- Note: id is SERIAL, we change it to BIGINT and update sequence
ALTER TABLE chat_message_embedding ALTER COLUMN id TYPE BIGINT;
ALTER SEQUENCE IF EXISTS chat_message_embedding_id_seq AS BIGINT;

ALTER TABLE chat_message_embedding ALTER COLUMN scenario_id TYPE BIGINT;
ALTER TABLE chat_message_embedding ALTER COLUMN suspect_id TYPE BIGINT;
ALTER TABLE chat_message_embedding ALTER COLUMN clue_id TYPE BIGINT;


-- 3. Re-create Foreign Keys
-- Now that all referenced and referencing columns are BIGINT, we can restore integrity.

-- location
ALTER TABLE location ADD CONSTRAINT location_scenario_id_fkey 
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE;

-- visibility_rule
ALTER TABLE visibility_rule ADD CONSTRAINT visibility_rule_scenario_id_fkey 
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE;

-- access_rule
ALTER TABLE access_rule ADD CONSTRAINT access_rule_scenario_id_fkey 
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE;

-- required_clue
ALTER TABLE required_clue ADD CONSTRAINT required_clue_scenario_id_fkey 
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE;

-- suspect
ALTER TABLE suspect ADD CONSTRAINT suspect_scenario_id_fkey 
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE;

-- suspect_timeline
-- References suspect(scenario_id, suspect_id)
ALTER TABLE suspect_timeline ADD CONSTRAINT suspect_timeline_scenario_id_suspect_id_fkey 
    FOREIGN KEY (scenario_id, suspect_id) REFERENCES suspect(scenario_id, suspect_id) ON DELETE CASCADE;

-- suspect_secret
-- References suspect(scenario_id, suspect_id)
ALTER TABLE suspect_secret ADD CONSTRAINT suspect_secret_scenario_id_suspect_id_fkey 
    FOREIGN KEY (scenario_id, suspect_id) REFERENCES suspect(scenario_id, suspect_id) ON DELETE CASCADE;

-- clue
ALTER TABLE clue ADD CONSTRAINT clue_scenario_id_fkey 
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE;

-- game_session
ALTER TABLE game_session ADD CONSTRAINT game_session_scenario_id_fkey 
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE;

-- chat_message_embedding
ALTER TABLE chat_message_embedding ADD CONSTRAINT chat_message_embedding_scenario_id_fkey 
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id) ON DELETE CASCADE;
