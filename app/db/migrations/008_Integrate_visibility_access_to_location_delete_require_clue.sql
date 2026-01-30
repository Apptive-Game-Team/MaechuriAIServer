-- Locaiton에 can_see와 cannot_see를 location_id를 스스로 참조하는 col 생성
-- access_rule 생성
-- 이후 visibility_rule에서 참조하여 기존에 있던 자료들 넘길 수 있도록 수정
-- 동일하게 access_rule에도 적용
-- visibility_rule, access_rule, require_clue 테이블 제거

-- 1. Location 테이블에 새 컬럼 추가
ALTER TABLE location ADD COLUMN can_see JSONB DEFAULT '[]';
ALTER TABLE location ADD COLUMN cannot_see JSONB DEFAULT '[]';
ALTER TABLE location ADD COLUMN access_requires VARCHAR(100);

-- 2. visibility_rule에서 기존 데이터 이전
UPDATE location l
SET can_see = vr.can_see,
    cannot_see = vr.cannot_see
FROM visibility_rule vr
WHERE l.scenario_id = vr.scenario_id
  AND l.location_id = vr.from_location_id;

-- 3. access_rule에서 기존 데이터 이전
UPDATE location l
SET access_requires = ar.requires
FROM access_rule ar
WHERE l.scenario_id = ar.scenario_id
  AND l.location_id = ar.location_id;

-- 4. 기존 테이블 삭제
DROP TABLE visibility_rule;
DROP TABLE access_rule;
DROP TABLE required_clue;