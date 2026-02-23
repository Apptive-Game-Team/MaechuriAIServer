-- ============================================================
-- Migration 014: Integrate map table into location table
-- ============================================================

-- 1. location 테이블에 컬럼 추가 및 제약 조건 설정
ALTER TABLE location
    ADD COLUMN type    VARCHAR(20) NOT NULL DEFAULT 'room'
                       CHECK (type IN ('room', 'corridor')),
    ADD COLUMN x       SMALLINT,
    ADD COLUMN y       SMALLINT,
    ADD COLUMN width   SMALLINT,
    ADD COLUMN height  SMALLINT;

-- 2. 기존 'room' 데이터 업데이트
-- map 테이블의 정보를 기반으로 기존 location 행들의 좌표 정보를 채웁니다.
UPDATE location l
SET
    type   = 'room',
    x      = m.x,
    y      = m.y,
    width  = m.width,
    height = m.height
FROM map m
WHERE l.scenario_id = m.scenario_id
  AND l.name        = m.name
  AND m.type        = 'room';

-- 3. 'corridor' 데이터를 신규 행으로 삽입 (중복 해결 버전)
-- JOIN을 제거하고 서브쿼리로 max_loc_id를 가져와서 1:N 뻥튀기를 방지합니다.
WITH corridors AS (
    SELECT
        m.scenario_id,
        m.name,
        m.x,
        m.y,
        m.width,
        m.height,
        -- 각 시나리오별 현재 최대 location_id를 서브쿼리로 계산
        (SELECT COALESCE(MAX(location_id), 0)
         FROM location
         WHERE scenario_id = m.scenario_id) AS max_loc_id,
        -- 삽입될 순번 계산
        ROW_NUMBER() OVER (PARTITION BY m.scenario_id ORDER BY m.map_id) AS rn
    FROM map m
    WHERE m.type = 'corridor'
)
INSERT INTO location (scenario_id, location_id, name, type, x, y, width, height)
SELECT
    scenario_id,
    max_loc_id + rn,
    name,
    'corridor',
    x,
    y,
    width,
    height
FROM corridors;

-- 4. 타입 필터링 성능을 위한 인덱스 추가
CREATE INDEX idx_location_type ON location(scenario_id, type);

-- [검증 쿼리 - DROP 하기 전에 실행해서 개수가 맞는지 확인하세요]
-- SELECT scenario_id, type, COUNT(*) FROM location GROUP BY scenario_id, type;
-- SELECT COUNT(*) FROM map WHERE type = 'corridor';

-- 5. 검증이 완료되었다면 map 테이블 삭제
DROP TABLE IF EXISTS map;