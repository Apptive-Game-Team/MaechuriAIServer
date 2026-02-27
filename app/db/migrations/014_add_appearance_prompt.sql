-- Migration 014: Add visual_description column to suspect and clue tables
-- 이미지 생성을 위한 생김새 프롬프트 컬럼 추가

ALTER TABLE suspect
    ADD COLUMN IF NOT EXISTS visual_description TEXT;

ALTER TABLE clue
    ADD COLUMN IF NOT EXISTS visual_description TEXT;
