import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.schemas import ClueItemSchema
from app.services.agent.suspect_actor import SuspectActor
from app.services.agent.suspect_generator import SuspectGenerator
from app.services.npc.formatters import ChatFormatter
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
        clue_added: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "user": user_message,
            "assistant": assistant_message,
            "pressure": pressure,
            "pressure_delta": pressure_delta,
            "tier": tier,
            "clue_added": clue_added or [],
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
        clue_id = i + 1
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
    SuspectActor 단일 LLM 호출로 대화 테스트.
    Judge + Actor 통합된 arespond() 사용.
    """
    llm = GeminiClient()
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

    # Pre-compute immutable suspect facts
    suspect_facts = ChatFormatter.format_facts(suspect.facts)

    print(f"\n{'='*60}")
    print(f"  Session: {session_id}")
    print(f"  Suspect: {suspect.name} ({suspect.role})")
    print(f"  Is Culprit: {suspect.is_culprit}")
    print(f"{'='*60}")
    print("\nCommands:")
    print("  'exit'     - 대화 종료")
    print("  'status'   - 현재 pressure 상태 확인")
    print("  'clue'     - 단서 제시 (ID 입력)")
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
            print(f"[STATUS] Clue Seen: {state.clue_seen_ids}\n")
            continue

        if user_input.lower() == 'cheat':
            old_pressure = state.current_pressure
            state.update_pressure(30)
            print(f"\n[CHEAT] Pressure: {old_pressure} -> {state.current_pressure} ({state.get_pressure_tier()})\n")
            continue

        # Clue presentation
        clue = None
        if user_input.lower() == 'clue':
            try:
                cid = int(input("Clue ID: ").strip())
                clue = {"id": cid, "name": f"단서 #{cid}", "description": "테스트 단서"}
                state.add_clue(cid)
                user_input = f"이 단서를 보세요. (단서 ID: {cid})"
                print(f"[CLUE] 단서 #{cid} 제시됨")
            except ValueError:
                print("잘못된 ID입니다.")
                continue

        # Single LLM call: Judge + Actor
        old_pressure = state.current_pressure
        result = asyncio.run(actor.arespond(
            user_message=user_input,
            suspect=suspect,
            state=state,
            clue_presented=clue,
            suspect_facts=suspect_facts,
        ))

        # Update pressure
        new_pressure = state.update_pressure(result.pressure_delta)

        # Display
        delta_str = f"+{result.pressure_delta}" if result.pressure_delta >= 0 else str(result.pressure_delta)
        print(f"\n[Pressure: {old_pressure} -> {new_pressure} ({delta_str}) | {state.get_pressure_tier()}]")
        print(f"[Strategy: {result.detected_strategy}]")
        print(f"\n{suspect.name}: {result.response}\n")

        # Save to log
        store.append_turn(
            session_id=session_id,
            user_message=user_input,
            assistant_message=result.response,
            pressure=new_pressure,
            pressure_delta=result.pressure_delta,
            tier=state.get_pressure_tier(),
            clue_added=[clue] if clue else []
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
