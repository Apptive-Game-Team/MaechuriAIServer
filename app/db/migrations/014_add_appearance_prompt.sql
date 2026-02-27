-- Migration 014: Add appearance_prompt column to suspect and clue tables
-- 이미지 생성을 위한 생김새 프롬프트 컬럼 추가

ALTER TABLE suspect
    ADD COLUMN IF NOT EXISTS appearance_prompt TEXT;

ALTER TABLE clue
    ADD COLUMN IF NOT EXISTS appearance_prompt TEXT;
