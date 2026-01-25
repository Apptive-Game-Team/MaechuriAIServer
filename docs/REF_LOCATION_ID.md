# Location 참조 방식 변경: Name → ID 기반 리팩토링

본 문서는 시나리오 내 장소(`Location`) 참조 방식을 기존의 **이름(String) 기반**에서 **ID(Integer, Foreign Key) 기반**으로 변경한 작업 내용을 정리합니다.

## 1. 배경 및 목적

기존에는 `VisibilityRule`, `AccessRule`, `Clue`, `SuspectTimeline` 등의 테이블에서 장소를 참조할 때 `"거실"`, `"주방"`과 같은 **문자열(이름)**을 직접 사용했습니다.

이로 인해 발생할 수 있는 문제점들은 다음과 같습니다:
1.  **참조 무결성 위협:** 오타 발생 시 관계가 끊어짐.
2.  **데이터 중복:** 같은 이름이 여러 번 저장됨.
3.  **관리의 어려움:** 장소 이름 변경 시 모든 참조 테이블을 찾아 수정해야 함.

따라서 데이터베이스 레벨에서는 **`location_id` (BIGINT)**를 사용하여 참조 무결성을 강화하고, 애플리케이션 레벨(AI, API)에서는 기존과 동일하게 **이름(String)**을 사용하여 가독성을 유지하는 방향으로 리팩토링을 진행했습니다.

---

## 2. 데이터베이스 스키마 변경

`app/db/migrations/005_refactor_location_refs.sql` 및 `db/schema.sql`에 반영된 변경 사항입니다.

### 2.1. 주요 변경 사항
*   모든 위치 참조 컬럼을 `VARCHAR`에서 `BIGINT`로 변경하고, `location` 테이블에 대한 `FOREIGN KEY` 제약 조건을 추가했습니다.
*   `JSONB` 컬럼(`can_see`, `cannot_see`) 내부의 데이터도 이름 리스트에서 **ID 리스트**로 변경했습니다.

### 2.2. 테이블별 상세 변경

| 테이블 | 컬럼 변경 | 설명 |
| :--- | :--- | :--- |
| **VisibilityRule** | `from_location` (String) → `from_location_id` (BigInt) | `Location` 테이블 FK 참조 |
| | `can_see`, `cannot_see` (JSONB) | 내부 값이 `["거실"]` → `[1]` 형태로 변경 |
| **AccessRule** | `location` (String) → `location_id` (BigInt) | 접근 제한 대상 장소 ID |
| **Clue** | `found_at` (String) → `location_id` (BigInt) | 단서 발견 장소 ID |
| **SuspectTimeline** | `location` (String) → `location_id` (BigInt) | 용의자 동선 위치 ID |

---

## 3. 애플리케이션 로직 변경

`ScenarioRepository`에서 DB 저장 및 조회 시 **자동 매핑(Mapping)** 로직을 추가하여, 외부(API, AI)에서는 여전히 이름을 사용할 수 있도록 처리했습니다.

### 3.1. 저장 로직 (`save_scenario`)
시나리오 생성 결과를 DB에 저장할 때:
1.  **`Location` 우선 저장 & 매핑 생성:**
    *   장소 목록을 먼저 DB에 저장(`insert`)하면서, `{"거실": 1, "주방": 2, ...}` 형태의 `name_to_id` 맵을 메모리에 생성합니다.
2.  **참조 데이터 변환:**
    *   다른 테이블(`Clue`, `Timeline` 등) 저장 시, 위 맵을 사용하여 이름(`"거실"`)을 ID(`1`)로 변환하여 저장합니다.
    *   `can_see`와 같은 리스트도 `[map["거실"], map["주방"]]` 형태로 변환합니다.

### 3.2. 조회 로직 (`_scenario_to_dict`, `get_...`)
DB에서 시나리오를 불러올 때:
1.  **매핑 생성:**
    *   해당 시나리오의 모든 `Location`을 조회하여 `{1: "거실", 2: "주방", ...}` 형태의 `id_to_name` 맵을 생성합니다.
2.  **데이터 복원:**
    *   스키마(Schema) 객체로 변환할 때, ID(`1`)를 다시 이름(`"거실"`)으로 변환하여 할당합니다.
    *   이로 인해 API 응답이나 프롬프트에는 사람이 읽기 편한 이름이 전달됩니다.

---

## 4. 기대 효과

*   **데이터 무결성 보장:** DB 수준에서 존재하지 않는 장소를 참조하는 것을 원천 차단(`FOREIGN KEY constraint`).
*   **성능 최적화:** 문자열 비교 대신 정수형 ID 비교 및 조인을 사용하여 DB 성능 향상.
*   **유지보수 용이성:** 장소 이름이 바뀌어도 `Location` 테이블의 `name`만 수정하면 되며, 참조하는 다른 테이블들은 수정할 필요가 없음.
*   **호환성 유지:** AI 및 프론트엔드 로직은 수정 없이 그대로 이름 기반으로 동작 가능.
