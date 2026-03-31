-- Migration 013: Drop critical_clue_ids from suspect table
-- This field was hallucinated by the LLM during generation (suspects are created before clues exist)
-- and had no active consumers.

ALTER TABLE suspect DROP COLUMN IF EXISTS critical_clue_ids;
