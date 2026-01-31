# API Testing Scenario: General Chat

This document provides test scenarios for the unified `/api/chats/general` endpoint.

## Endpoint

```
POST /api/chats/general
```

## Request Schema

```json
{
  "session_id": "string (UUID)",
  "scenario_id": integer,
  "user_message": "string"
}
```

## Response Schema

```json
{
  "user_message": "string",
  "answer": "string"
}
```

---

## Test Scenarios

### 1. General Question - Case Overview

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": 1,
  "user_message": "사건이 언제 일어났어요?"
}
```

**Expected Response:**
```json
{
  "user_message": "사건이 언제 일어났어요?",
  "answer": "사건은 새벽 1시 30분에서 2시 15분 사이에 발생한 것으로 추정됩니다..."
}
```

---

### 2. Clue Reference - Evidence Analysis

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": 1,
  "user_message": "[c:1] 이게 뭐야?"
}
```

**Expected Response:**
```json
{
  "user_message": "[c:1] 이게 뭐야?",
  "answer": "이 메모를 보니... 복잡한 수식이 적혀있는데, 변수 표기가 일반적이지 않네요."
}
```

---

### 3. Clue Reference - Ask for Meaning

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": 1,
  "user_message": "[c:1] 이게 무슨 의미야?"
}
```

**Expected Response:**
```json
{
  "user_message": "[c:1] 이게 무슨 의미야?",
  "answer": "제가 보기에 이건 'PARK'를 가리키는 것 같습니다. 어떻게 그런 결론이 나왔는지는... 직접 한번 살펴보시겠어요?"
}
```

**Note:** The detective shares the decoded meaning but does NOT explain the logic.

---

### 4. Suspect Reference

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": 1,
  "user_message": "[s:1] 이 용의자에 대해 알려줘"
}
```

**Expected Response:**
```json
{
  "user_message": "[s:1] 이 용의자에 대해 알려줘",
  "answer": "김철수 씨는 피해자의 동료입니다. 사건 당시 자택에 있었다고 주장하고 있어요..."
}
```

---

### 5. Ask Who Did It

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": 1,
  "user_message": "누가 범인이에요?"
}
```

**Expected Response:**
```json
{
  "user_message": "누가 범인이에요?",
  "answer": "아직 단정짓기는 이릅니다. 증거들을 더 살펴보고, 용의자들의 진술을 확인해봐야 할 것 같습니다."
}
```

---

### 6. Multiple References

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario_id": 1,
  "user_message": "[c:1]이랑 [c:2] 연관이 있어?"
}
```

**Expected Response:**
```json
{
  "user_message": "[c:1]이랑 [c:2] 연관이 있어?",
  "answer": "흠... 두 증거를 함께 보니 뭔가 연결고리가 있는 것 같기도 하네요. 직접 살펴보시겠어요?"
}
```

---

## Reference Format

| Format | Description | Example |
|--------|-------------|---------|
| `[c:ID]` | Clue/Evidence reference | `[c:1]`, `[c:02]` |
| `[s:ID]` | Suspect reference | `[s:1]`, `[s:02]` |

---

## Detective Response Guidelines

### What the Detective WILL Do:
- Describe physical observations of evidence
- Share decoded meanings when asked
- Provide case timeline and location info
- List suspects with basic profiles
- Express doubt about red herrings

### What the Detective WILL NOT Do:
- Reveal who the culprit is
- Explain murder method or motive
- **Explain logic/reasoning** (guides user to infer)
- Use game-related terms ("hint", "player", "level")
- Say "정답은..." or "이건 힌트인데요"

---

## cURL Examples

### General Question
```bash
curl -X POST "http://localhost:8000/api/chats/general" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "scenario_id": 1,
    "user_message": "사건이 언제 일어났어요?"
  }'
```

### Evidence Analysis
```bash
curl -X POST "http://localhost:8000/api/chats/general" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "scenario_id": 1,
    "user_message": "[c:1] 이게 무슨 의미야?"
  }'
```

---

## Migration from `/api/chats/clue`

The `/api/chats/clue` endpoint is **deprecated**.

### Before (Deprecated)
```json
POST /api/chats/clue
{
  "session_id": "...",
  "scenario_id": 1,
  "clue_id": 1,
  "user_message": "이게 무슨 의미야?"
}
```

### After (Recommended)
```json
POST /api/chats/general
{
  "session_id": "...",
  "scenario_id": 1,
  "user_message": "[c:1] 이게 무슨 의미야?"
}
```
