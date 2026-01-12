import json
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가하여 app 모듈을 찾을 수 있게 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.agent.map_generator import MapGenerator
from app.services.llm.gemini_client import GeminiClient
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas.clue import ClueSetSchema

def test_map_generation():
    # 1. Load test data
    file_path = 'app/test/result_20260108_161239.json'
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Test data file not found at {file_path}")
        return

    # 2. Separate clues and scenario data
    if 'clues' in data:
        clues_data = data.pop('clues')
    else:
        print("Error: 'clues' field missing in test data")
        return

    # 3. Validate and create model instances
    try:
        scenario = ScenarioExpansion(**data)
        clues = ClueSetSchema(**clues_data)
    except Exception as e:
        print(f"Error validating input data: {e}")
        return

    print("Data loaded and validated successfully.")

    # 4. Initialize services
    try:
        llm_client = GeminiClient()
        map_generator = MapGenerator(llm_client)
    except RuntimeError as e:
        print(f"Error initializing services (check API Key): {e}")
        return

    # 5. Generate Map
    print("Generating map... (this may take a few seconds)")
    try:
        result = map_generator.generate_map(scenario, clues)
        print("\n=== Map Generation Result ===")
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error during map generation: {e}")

if __name__ == "__main__":
    test_map_generation()
