-- Migration 020: Create furniture table for room decoration items.

CREATE TABLE IF NOT EXISTS furniture (
    id          BIGSERIAL PRIMARY KEY,
    scenario_id BIGINT NOT NULL,
    location_id BIGINT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    origin_x    INTEGER NOT NULL,
    origin_y    INTEGER NOT NULL,
    width       INTEGER NOT NULL,
    height      INTEGER NOT NULL,
    assets_url  VARCHAR(500),
    CONSTRAINT fk_furniture_location
        FOREIGN KEY (scenario_id, location_id)
        REFERENCES location (scenario_id, location_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_furniture_scenario
ON furniture (scenario_id);
