import json
import os
from datetime import datetime

from app.services.llm.gemini_client import GeminiClient
from app.services.scenario.scenario_service import ScenarioService

def test_scenario():
    print("SCENARIO TEST START")

    agent = ScenarioService(GeminiClient())
    test_dict = agent.generate("밀실 방화 사망 사건")

    print(test_dict)
    # 결과 저장 (현재 시각 기준 파일명)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"result_{timestamp}.json"
    
    # 스크립트와 같은 위치에 저장
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(test_dict, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResult saved to: {file_path}")