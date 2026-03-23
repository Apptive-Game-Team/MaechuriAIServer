-- Migration 019: Add composite index for efficient fact retrieval by pressure threshold.
-- Optimizes get_all_accessible_facts() which filters on (scenario_id, suspect_id, threshold).

CREATE INDEX IF NOT EXISTS idx_fact_scenario_suspect_threshold
ON fact (scenario_id, suspect_id, threshold ASC);
