-- Migration 018: Add knowledge_type column to fact table
-- Distinguishes between timeline (first-hand), heard (second-hand),
-- secret (reluctant but honest), and hidden (culprit actively lying).

-- 1. Add column as nullable first to allow backfill
ALTER TABLE fact ADD COLUMN knowledge_type VARCHAR(50);

-- 2. Backfill existing suspect facts based on their existing type
UPDATE fact SET knowledge_type = 'timeline' WHERE type = 'timeline' AND suspect_id > 0;
UPDATE fact SET knowledge_type = 'secret'   WHERE type = 'secret'   AND suspect_id > 0;

-- 3. Backfill context facts (suspect_id = 0)
UPDATE fact SET knowledge_type = 'context'  WHERE suspect_id = 0;

-- 4. Set NOT NULL constraint with a safe default for any stragglers
UPDATE fact SET knowledge_type = 'timeline' WHERE knowledge_type IS NULL AND suspect_id > 0;
UPDATE fact SET knowledge_type = 'context'  WHERE knowledge_type IS NULL AND suspect_id = 0;

ALTER TABLE fact ALTER COLUMN knowledge_type SET DEFAULT 'timeline';
ALTER TABLE fact ALTER COLUMN knowledge_type SET NOT NULL;

-- 5. Update type check constraint to allow 'heard'
ALTER TABLE fact DROP CONSTRAINT IF EXISTS check_fact_type;
ALTER TABLE fact ADD CONSTRAINT check_fact_type
  CHECK (type IN ('secret', 'timeline', 'heard', 'incident', 'location', 'world'));

-- 6. Add knowledge_type check constraint
ALTER TABLE fact DROP CONSTRAINT IF EXISTS check_knowledge_type;
ALTER TABLE fact ADD CONSTRAINT check_knowledge_type
  CHECK (
    (suspect_id = 0 AND knowledge_type IN ('context', 'timeline')) OR
    (suspect_id > 0 AND knowledge_type IN ('timeline', 'heard', 'secret', 'hidden'))
  );
