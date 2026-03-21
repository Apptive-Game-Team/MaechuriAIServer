-- Migration 018: Extend fact.type to support heard/hidden types
-- No new column needed — reuse existing `type` column.
-- heard = second-hand knowledge about other suspects
-- hidden = facts the culprit is actively lying about (subset of secrets)

-- 1. Update type check constraint to allow 'heard' and 'hidden'
ALTER TABLE fact DROP COLUMN IF EXISTS knowledge_type;
ALTER TABLE fact DROP CONSTRAINT IF EXISTS check_fact_type;
ALTER TABLE fact ADD CONSTRAINT check_fact_type
  CHECK (type IN ('secret', 'hidden', 'timeline', 'heard', 'incident', 'location', 'world'));
