-- Migration: Merge scenario_context into fact table
-- scenario_context 테이블 데이터를 fact 테이블로 이전 후 삭제
-- suspect_id = 0 for scenario-level context (detective-accessible)

-- 1. fact 테이블에서 suspect FK 제약 삭제
ALTER TABLE fact DROP CONSTRAINT IF EXISTS fact_scenario_id_suspect_id_fkey;

-- 2. scenario_context가 존재하면 데이터 이전
DO $$
DECLARE
    max_fact_id INT;
    r RECORD;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'scenario_context') THEN
        -- 각 시나리오별로 처리
        FOR r IN (SELECT DISTINCT scenario_id FROM scenario_context) LOOP
            -- 해당 시나리오의 최대 fact_id 조회
            SELECT COALESCE(MAX(fact_id), 0) INTO max_fact_id
            FROM fact WHERE scenario_id = r.scenario_id;

            -- context를 fact로 이전 (row_number로 순차 fact_id 생성)
            INSERT INTO fact (scenario_id, fact_id, suspect_id, threshold, type, content, embedding)
            SELECT
                sc.scenario_id,
                max_fact_id + ROW_NUMBER() OVER (ORDER BY sc.context_id) AS fact_id,
                0 AS suspect_id,
                0 AS threshold,
                sc.type,
                jsonb_build_object('text', sc.content, 'extra_data', sc.extra_data) AS content,
                sc.embedding
            FROM scenario_context sc
            WHERE sc.scenario_id = r.scenario_id;
        END LOOP;

        -- scenario_context 테이블 삭제
        DROP TABLE scenario_context;
    END IF;
END $$;

-- 3. type 체크 제약 업데이트 (context types 추가)
ALTER TABLE fact DROP CONSTRAINT IF EXISTS check_fact_type;
ALTER TABLE fact ADD CONSTRAINT check_fact_type
    CHECK (type IN ('secret', 'timeline', 'incident', 'location', 'world'));

-- 4. suspect_id에 기본값 0 설정
ALTER TABLE fact ALTER COLUMN suspect_id SET DEFAULT 0;

-- 5. threshold에 기본값 0 설정
ALTER TABLE fact ALTER COLUMN threshold SET DEFAULT 0;
