-- Migration 022: Link furniture/suspect/clue to asset table
-- furniture.assets_url → asset_id FK, suspect/clue에 asset_id 추가
-- asset 테이블에 description, type 컬럼 추가, name nullable 변경

-- 1. Asset table changes
ALTER TABLE asset ALTER COLUMN name DROP NOT NULL;
ALTER TABLE asset ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE asset ADD COLUMN IF NOT EXISTS type VARCHAR(20);

-- 2. Furniture: drop legacy column, add FK
ALTER TABLE IF EXISTS furniture
    DROP COLUMN IF EXISTS assets_url,
    ADD COLUMN IF NOT EXISTS asset_id BIGINT;

alter table furniture ADD CONSTRAINT fk_furniture_asset FOREIGN KEY (asset_id) REFERENCES asset(id);
