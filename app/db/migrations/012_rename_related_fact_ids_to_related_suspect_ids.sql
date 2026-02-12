-- ============================================================
-- Migration 012: Rename related_fact_ids to related_suspect_ids
-- The column actually stores suspect IDs, not fact IDs.
-- ============================================================

ALTER TABLE clue RENAME COLUMN related_fact_ids TO related_suspect_ids;
