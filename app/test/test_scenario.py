import json
import os
from datetime import datetime

from app.services.llm.gemini_client import GeminiClient
from app.services.scenario.scenario_service import ScenarioService
from app.models.schemas.scenario import ScenarioResult


def test_scenario():
    print("SCENARIO TEST START")

    agent = ScenarioService(GeminiClient())
    test_str = "ed4acf8d-bc30-4e52-9a6e-f062726d128d"
    # request_id = datetime.now().strftime("%y_%m_%d_%H_%M_test")
    scenario_result = agent.generate("밀실 방화 사망 사건", test_str)

    print(scenario_result)
    # 결과 저장 (현재 시각 기준 파일명)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"result_{timestamp}.json"

    # 스크립트와 같은 위치에 저장
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(scenario_result.model_dump(mode='json'), f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResult saved to: {file_path}")


async def test_save_scenario():
    agent = ScenarioService(GeminiClient())

    from app.db.database import async_session_factory

    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'result_20260127_173313.json')

    with open(file_path, 'r', encoding='utf-8') as f:
        scenario_data = json.load(f)

    if scenario_data is None:
        raise Exception("Scenario Data Not Found")

    # Parse dict to ScenarioResult for type safety
    scenario_result = ScenarioResult.model_validate(scenario_data)

    async with async_session_factory() as db:
        await agent.save_to_db(scenario_result, db)

        print("Successfully generated and saved scenario")