# /api/scenarios/solve 엔드포인트 문서

> 유저의 추리를 검증하는 엔드포인트 구현 문서

---

## 1. 개요

유저가 제출한 범인과 추리 내용을 검증하여 점수와 피드백을 제공합니다.

### 검증 방식
- **임베딩 유사도 + LLM 하이브리드**
- 범인 ID 필수 검증 (틀리면 즉시 오답)
- 유사도 높으면 LLM 호출 생략 (비용 절감)

---

## 2. API 스펙

### Request

```http
POST /api/scenarios/solve
Content-Type: application/json
```

```json
{
  "scenario_id": 1,
  "culprit_id": [2],
  "user_solution": "범인은 김철수입니다. 그는 금전 분쟁으로 인해..."
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `scenario_id` | int | O | 시나리오 ID |
| `culprit_id` | int[] | O | 범인 ID 목록 (min: 1) |
| `user_solution` | string | O | 추리 내용 (10~2000자) |

### Response

```json
{
  "scenario_id": 1,
  "status": "correct",
  "success": true,
  "culprit_score": 100.0,
  "reasoning_score": 85.0,
  "total_score": 91.0,
  "culprit_match": {
    "expected": [2],
    "submitted": [2],
    "is_match": true,
    "match_rate": 1.0
  },
  "similarity_score": 0.82,
  "message": "축하합니다! 정확한 추리입니다.",
  "feedback": "범인과 동기, 수법을 모두 정확하게 파악했습니다.",
  "hints": null
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | enum | `correct`, `partial`, `incorrect` |
| `success` | bool | 성공 여부 (CORRECT일 때 true) |
| `culprit_score` | float | 범인 점수 (0 or 100) |
| `reasoning_score` | float | 추리 점수 (0~100) |
| `total_score` | float | 총점 (범인 40% + 추리 60%) |
| `culprit_match` | object | 범인 매칭 상세 |
| `similarity_score` | float? | 임베딩 유사도 (0~1) |
| `message` | string | 결과 메시지 |
| `feedback` | string? | 상세 피드백 |
| `hints` | string[]? | 힌트 (오답/부분정답 시) |

---

## 3. 검증 흐름

```
┌─────────────────────────────────────┐
│  1. 시나리오 데이터 조회            │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  2. 범인 ID 검증                    │
│     expected vs submitted           │
└─────────────────┬───────────────────┘
                  ▼
         ┌───────┴───────┐
         │  일치 여부?   │
         └───────┬───────┘
          불일치 │        │ 일치
                 ▼        ▼
    ┌────────────────┐   ┌────────────────────────┐
    │ INCORRECT      │   │ 3. Ground Truth 생성   │
    │ 즉시 반환      │   │    (범인+동기+수법+    │
    └────────────────┘   │     시간+장소)         │
                         └───────────┬────────────┘
                                     ▼
                         ┌────────────────────────┐
                         │ 4. 임베딩 유사도 계산  │
                         │    (BGE-M3 코사인)     │
                         └───────────┬────────────┘
                                     ▼
                         ┌───────────┴───────────┐
                         │ 유사도 >= 0.7 ?       │
                         └───────────┬───────────┘
                          Yes │           │ No
                              ▼           ▼
                    ┌──────────────┐  ┌──────────────────┐
                    │ 정답 처리    │  │ 5. LLM 검증      │
                    │ (LLM 생략)   │  │    (SolveValidator)│
                    └──────────────┘  └─────────┬────────┘
                                                ▼
                         ┌────────────────────────────────┐
                         │ 6. 최종 점수 계산 및 응답 생성 │
                         │    - 범인 점수 (40%)           │
                         │    - 추리 점수 (60%)           │
                         │    - 상태 결정                 │
                         └────────────────────────────────┘
```

---

## 4. 결과 상태

| 상태 | 조건 | success |
|------|------|---------|
| `CORRECT` | 범인 맞음 + 추리 >= 70점 | true |
| `PARTIAL` | 범인 맞음 + 추리 < 70점 | false |
| `INCORRECT` | 범인 틀림 | false |

---

## 5. 점수 체계

### 총점 계산
```
total_score = (culprit_score × 0.4) + (reasoning_score × 0.6)
```

### 범인 점수
- 일치: 100점
- 불일치: 0점

### 추리 점수 (LLM 검증 시)

| 요소 | 배점 | 설명 |
|------|------|------|
| 범인 | 20점 | 범인 이름 언급 정확도 |
| 동기 | 20점 | 범행 동기 파악 |
| 수법 | 20점 | 범행 방법 설명 |
| 시간 | 20점 | 범행 시간 파악 |
| 장소 | 20점 | 범행 장소 파악 |

---

## 6. 설정값

| 상수 | 값 | 설명 |
|------|-----|------|
| `SIMILARITY_THRESHOLD` | 0.7 | 유사도 임계값 |
| `PASSING_SCORE` | 70 | 통과 점수 |
| `CULPRIT_WEIGHT` | 0.4 | 범인 점수 가중치 |
| `REASONING_WEIGHT` | 0.6 | 추리 점수 가중치 |

---

## 7. 파일 구조

```
app/
├── models/schemas/
│   └── solve.py                 # 스키마 정의
│       ├── SolveResultStatus    # Enum (CORRECT/PARTIAL/INCORRECT)
│       ├── CulpritMatchResult   # 범인 매칭 결과
│       ├── ScenarioSolveRequest # 요청 모델
│       ├── ScenarioSolveResponse# 응답 모델
│       └── SolveValidationResult# LLM 검증 결과 (내부용)
│
├── prompts/solve/
│   └── system.txt               # LLM 검증 프롬프트
│
├── services/
│   ├── agent/
│   │   └── solve_validator.py   # LLM 검증기
│   │       └── SolveValidator.validate()
│   │
│   └── scenario/
│       └── solve_service.py     # 핵심 서비스
│           └── SolveService.solve()
│
├── api/
│   ├── dependencies/
│   │   └── scenario_dependencies.py
│   │       └── get_solve_service()
│   │
│   └── routes/
│       └── scenario.py
│           └── solve_scenario()  # POST /solve
```

---

## 8. 코드 상세

### 8.1 SolveService 핵심 로직

```python
# app/services/scenario/solve_service.py

class SolveService:
    async def solve(self, scenario_id, submitted_culprit_ids, user_solution):
        # 1. 시나리오 조회
        scenario_data = await self.repository.get_scenario_by_id(scenario_id)

        # 2. 범인 ID 검증
        culprit_match = self._check_culprit_match(expected, submitted)
        if not culprit_match.is_match:
            return self._create_incorrect_response(...)

        # 3. Ground Truth 생성
        ground_truth = self._build_ground_truth_text(scenario_data)
        # "범인: X. 동기: Y. 수법: Z. 범행 시간: A. 범행 장소: B."

        # 4. 임베딩 유사도 계산
        similarity = self._calculate_similarity(ground_truth, user_solution)

        # 5. 분기 처리
        if similarity >= 0.7:
            reasoning_score = similarity * 100
            feedback = "추리가 정확합니다."
        else:
            validation = self.solve_validator.validate(ground_truth, user_solution)
            reasoning_score = validation.total_score
            feedback = validation.feedback

        # 6. 응답 생성
        return self._create_response(...)
```

### 8.2 Ground Truth 문장 형식

```python
def _build_ground_truth_text(self, scenario_data):
    # 시나리오에서 추출
    culprit_names = "김철수, 이영희"  # is_culprit=True인 용의자들
    motive = "금전 분쟁; 복수심"      # 범인들의 motive 결합
    method = "독살"                   # ground_truth_detail.method
    time = "22:00 ~ 23:00"           # crime_time_range
    location = "서재"                 # crime_location

    return f"범인: {culprit_names}. 동기: {motive}. 수법: {method}. 범행 시간: {time}. 범행 장소: {location}."
```

### 8.3 LLM 검증 프롬프트

```text
# app/prompts/solve/system.txt

[ROLE]
You are a MYSTERY SOLUTION VALIDATOR.
Evaluate player's reasoning against ground truth.

[INPUT]
- ground_truth: 정답 (범인, 동기, 수법, 시간, 장소)
- user_solution: 유저 추리

[OUTPUT]
{
  "culprit_score": 0-20,
  "motive_score": 0-20,
  "method_score": 0-20,
  "time_score": 0-20,
  "location_score": 0-20,
  "total_score": 0-100,
  "feedback": "피드백 (한국어)",
  "missing_elements": ["놓친 요소1", ...]
}

[SCORING]
- 정확: 20점
- 부분 정확: 10-15점
- 관련 있음: 5-10점
- 틀림/없음: 0점

[PRINCIPLES]
- 의미 기반 비교 (다른 표현도 인정)
- 부분 점수 허용
- 피드백은 한국어로
```

---

## 9. 에러 처리

| 상황 | HTTP 코드 | 응답 |
|------|----------|------|
| 시나리오 없음 | 404 | `Scenario {id} not found` |
| 범인 ID 없음 | 422 | Pydantic validation error |
| 추리 길이 부족 | 422 | Pydantic validation error |
| 서버 오류 | 500 | `Failed to evaluate solution` |

---

## 10. 사용 예시

### 정답 케이스
```bash
curl -X POST /api/scenarios/solve \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": 1,
    "culprit_id": [2],
    "user_solution": "범인은 김철수입니다. 그는 피해자와의 금전 분쟁으로 인해 22시경 서재에서 독을 사용하여 범행을 저질렀습니다."
  }'
```

```json
{
  "status": "correct",
  "success": true,
  "total_score": 94.0,
  "message": "축하합니다! 정확한 추리입니다."
}
```

### 부분정답 케이스
```json
{
  "status": "partial",
  "success": false,
  "total_score": 58.0,
  "message": "범인은 맞았지만, 추리가 완전하지 않습니다.",
  "hints": ["범행 시간 언급 없음", "동기 불분명"]
}
```

### 오답 케이스
```json
{
  "status": "incorrect",
  "success": false,
  "total_score": 0.0,
  "message": "범인을 잘못 지목했습니다.",
  "hints": ["용의자들의 알리바이를 다시 확인해보세요."]
}
```

---

## 11. 향후 개선 사항

- [ ] 다중 범인 부분 점수 지원
- [ ] 추리 히스토리 저장
- [ ] 힌트 레벨 조절 (난이도별)
- [ ] 제출 횟수 제한
- [ ] 리더보드 통합
