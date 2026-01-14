import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.schemas import ClueItemSchema
from app.services.agent.pressure_judge import PressureJudge
from app.services.agent.suspect_actor import SuspectActor
from app.services.agent.suspect_generator import SuspectGenerator
from app.services.llm.gemini_client import GeminiClient
from app.models.schemas.suspect import (
    SuspectGenerationRequest,
    CaseContextSchema,
    SuspectSchema
)
from app.models.schemas.scenario import (
    WorldContextSchema,
    GroundTruthSchema,
    ConstraintsSchema,
    SuspectGenConfig
)
from app.models.domain.suspect_state import SuspectState


class JsonlHistoryStore:
    def __init__(self, base_dir: str = "app/test/chat_logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def session_path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.jsonl"

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        pressure: int,
        pressure_delta: int,
        tier: str,
        evidence_added: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "user": user_message,
            "assistant": assistant_message,
            "pressure": pressure,
            "pressure_delta": pressure_delta,
            "tier": tier,
            "evidence_added": evidence_added or [],
        }
        with self.session_path(session_id).open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_suspect_generator():
    """Suspect Generator 테스트"""
    file_path = "app/test/result_20260108_164457.json"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        scenario_data = json.load(f)

    llm = GeminiClient()
    generator = SuspectGenerator(llm)

    # Case Context
    incident = scenario_data["incident"]
    case_context = CaseContextSchema(
        incident_time=incident["time_range"],
        primary_location=incident["location"],
        incident_type=incident["type"],
        summary=incident["summary"]
    )

    # World Context
    world_data = scenario_data.get("world_detail", scenario_data.get("world", {}))
    world_context = WorldContextSchema(**world_data)

    # Ground Truth
    gt_data = scenario_data.get("ground_truth_detail", scenario_data.get("ground_truth", {}))
    ground_truth = GroundTruthSchema(**gt_data)

    # Generation Config
    gen_targets = scenario_data["generation_targets"]
    suspect_config = SuspectGenConfig(**gen_targets["suspects"])

    # Clues
    clues_data = scenario_data.get("clues_detail", {}).get("clues", [])
    clues = []
    for i, c in enumerate(clues_data):
        clue_id = 101 + i
        clues.append(ClueItemSchema(id=clue_id, **c))

    # Constraints
    constraints_data = scenario_data.get("constraints")
    constraints = ConstraintsSchema(**constraints_data) if constraints_data else None

    # Build Request
    request = SuspectGenerationRequest(
        case_context=case_context,
        world_context=world_context,
        ground_truth=ground_truth,
        generation_config=suspect_config,
        clues=clues,
        constraints=constraints
    )

    print(">>> Generating Suspects...")
    try:
        result = generator.generate(request)
        print("\n>>> Generation Successful!")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"app/test/suspect_result_{timestamp}.json"

        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        print(f">>> Result saved to: {output_filename}")
    except Exception as e:
        print(f"\n>>> Generation Failed: {e}")
        import traceback
        traceback.print_exc()


def test_suspect_chat():
    """
    새로운 Pressure 시스템으로 Suspect와 대화 테스트.
    PressureJudge + SuspectActor 사용.
    """
    llm = GeminiClient()
    judge = PressureJudge(llm)
    actor = SuspectActor(llm)

    session_id = datetime.now().strftime("suspect_chat_%Y%m%d_%H%M%S")
    store = JsonlHistoryStore()

    # Load suspect data
    suspect_test_file_path = "app/test/suspect_test.json"
    if not os.path.exists(suspect_test_file_path):
        print(f"File not found: {suspect_test_file_path}")
        return

    with open(suspect_test_file_path, "r", encoding="utf-8") as f:
        suspect_data = json.load(f)

    # Validate as SuspectSchema
    suspect = SuspectSchema.model_validate(suspect_data)

    # Initialize state
    state = SuspectState(suspect_id=suspect.suspect_id)

    print(f"\n{'='*60}")
    print(f"  Session: {session_id}")
    print(f"  Suspect: {suspect.name} ({suspect.role})")
    print(f"  Is Culprit: {suspect.is_culprit}")
    print(f"{'='*60}")
    print("\nCommands:")
    print("  'exit'     - 대화 종료")
    print("  'status'   - 현재 pressure 상태 확인")
    print("  'evidence' - 증거 제시 (ID 입력)")
    print("  'cheat'    - pressure +30 (테스트용)")
    print(f"{'='*60}\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == 'exit':
            print("대화를 종료합니다.")
            break

        if user_input.lower() == 'status':
            print(f"\n[STATUS] Pressure: {state.current_pressure}/100 | Tier: {state.get_pressure_tier()}")
            print(f"[STATUS] Evidence Seen: {state.evidence_seen_ids}\n")
            continue

        if user_input.lower() == 'cheat':
            old_pressure = state.current_pressure
            state.update_pressure(30)
            print(f"\n[CHEAT] Pressure: {old_pressure} -> {state.current_pressure} ({state.get_pressure_tier()})\n")
            continue

        # Evidence presentation
        evidence = None
        if user_input.lower() == 'evidence':
            try:
                eid = int(input("Evidence ID: ").strip())
                evidence = {"id": eid, "name": f"증거 #{eid}", "description": "테스트 증거"}
                state.add_evidence(eid)
                user_input = f"이 증거를 보세요. (증거 ID: {eid})"
                print(f"[EVIDENCE] 증거 #{eid} 제시됨")
            except ValueError:
                print("잘못된 ID입니다.")
                continue

        # Create suspect summary for judge
        suspect_summary = f"이름: {suspect.name}, 역할: {suspect.role}, 범인여부: {suspect.is_culprit}"

        # Format timeline for judge
        timeline_str = "\n".join([
            f"- {t.time}: {t.location}에서 {t.activity} ({'증명가능' if t.can_prove else '미확인'})"
            for t in suspect.timeline
        ])

        # Format recent context
        recent_history = state.get_recent_history(5)
        context = "\n".join([f"{h['role']}: {h['content']}" for h in recent_history]) if recent_history else "(대화 시작)"

        # 1. Judge: pressure 변화량 평가 (alibi/timeline 정보 포함)
        judge_result = judge.evaluate(
            user_message=user_input,
            suspect_summary=suspect_summary,
            current_pressure=state.current_pressure,
            conversation_context=context,
            evidence_presented=evidence,
            suspect_alibi=suspect.alibi_summary,
            suspect_timeline=timeline_str
        )

        # 2. Update pressure
        old_pressure = state.current_pressure
        new_pressure = state.update_pressure(judge_result.pressure_delta)

        # 3. Actor: 응답 생성
        response = actor.generate_response(
            suspect=suspect,
            state=state,
            user_message=user_input,
            evidence_presented=evidence
        )

        # 4. Update history
        state.add_message("user", user_input)
        state.add_message("suspect", response)

        # 5. Display
        delta_str = f"+{judge_result.pressure_delta}" if judge_result.pressure_delta >= 0 else str(judge_result.pressure_delta)
        print(f"\n[Pressure: {old_pressure} -> {new_pressure} ({delta_str}) | {state.get_pressure_tier()}]")
        print(f"[Strategy: {judge_result.detected_strategy}]")
        print(f"\n{suspect.name}: {response}\n")

        # 6. Save to log
        store.append_turn(
            session_id=session_id,
            user_message=user_input,
            assistant_message=response,
            pressure=new_pressure,
            pressure_delta=judge_result.pressure_delta,
            tier=state.get_pressure_tier(),
            evidence_added=[evidence] if evidence else []
        )


if __name__ == "__main__":
    print("\n========================================")
    print("  Suspect System Test")
    print("========================================")
    print("1: Suspect Generator (용의자 생성)")
    print("2: Suspect Chat (대화 테스트)")
    print("========================================")

    choice = input("Select: ").strip()

    if choice == "1":
        test_suspect_generator()
    elif choice == "2":
        test_suspect_chat()
    else:
        print("Invalid choice.")
