"""
Map Generator 테스트
- generate_skeleton: 방 구조 + 복도 생성
- generate_detail: 오브젝트 배치
"""
import json
import os
import sys
from datetime import datetime

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.agent.map_generator import MapGenerator
from app.services.llm.gemini_client import GeminiClient
from app.models.schemas.scenario import ScenarioExpansion
from app.models.schemas.clue import ClueSetSchema

# 테스트 데이터 파일 경로
TEST_DATA_FILE = 'app/test/result_20260114_171359.json'
OUTPUT_DIR = 'app/test/output'


def save_result(data: dict, prefix: str) -> str:
    """결과를 JSON 파일로 저장"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{prefix}_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Result saved to: {filepath}")
    return filepath


def load_test_data():
    """테스트 데이터 로드 및 ScenarioExpansion, ClueSetSchema 추출"""
    try:
        with open(TEST_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Test data file not found at {TEST_DATA_FILE}")
        return None, None

    # ScenarioExpansion에 필요한 필드만 추출
    expansion_fields = [
        'meta', 'incident', 'world', 'ground_truth',
        'world_detail', 'ground_truth_detail', 'generation_targets', 'constraints'
    ]
    expansion_data = {k: data[k] for k in expansion_fields if k in data}

    # Clues 추출
    clues_data = data.get('clues', {})

    try:
        scenario = ScenarioExpansion(**expansion_data)
        clues = ClueSetSchema(**clues_data)
        return scenario, clues
    except Exception as e:
        print(f"Error validating input data: {e}")
        return None, None


def test_map_skeleton():
    """Map Skeleton 생성 테스트"""
    print("=" * 50)
    print("TEST: Map Skeleton Generation")
    print("=" * 50)

    scenario, _ = load_test_data()
    if scenario is None:
        return None

    try:
        llm_client = GeminiClient()
        map_generator = MapGenerator(llm_client)
    except RuntimeError as e:
        print(f"Error initializing services (check API Key): {e}")
        return None

    print("Generating map skeleton...")
    try:
        skeleton = map_generator.generate_skeleton(scenario)
        result_data = skeleton.model_dump()

        print("\n=== Map Skeleton Result ===")
        print(json.dumps(result_data, indent=2, ensure_ascii=False))

        save_result(result_data, "map_skeleton")
        return skeleton
    except Exception as e:
        print(f"Error during skeleton generation: {e}")
        return None


def test_map_detail(skeleton=None):
    """Map Detail 생성 테스트"""
    print("\n" + "=" * 50)
    print("TEST: Map Detail Generation")
    print("=" * 50)

    scenario, clues = load_test_data()
    if scenario is None or clues is None:
        return None

    # skeleton이 없으면 먼저 생성
    if skeleton is None:
        print("No skeleton provided, generating skeleton first...")
        skeleton = test_map_skeleton()
        if skeleton is None:
            return None

    try:
        llm_client = GeminiClient()
        map_generator = MapGenerator(llm_client)
    except RuntimeError as e:
        print(f"Error initializing services (check API Key): {e}")
        return None

    print("Generating map detail...")
    try:
        detail = map_generator.generate_detail(scenario, skeleton, clues)
        result_data = detail.model_dump()

        print("\n=== Map Detail Result ===")
        print(json.dumps(result_data, indent=2, ensure_ascii=False))

        save_result(result_data, "map_detail")
        return detail
    except Exception as e:
        print(f"Error during detail generation: {e}")
        return None


def test_full_pipeline():
    """전체 Map 생성 파이프라인 테스트"""
    print("\n" + "=" * 50)
    print("TEST: Full Map Generation Pipeline")
    print("=" * 50)

    # 1. Skeleton 생성
    skeleton = test_map_skeleton()
    if skeleton is None:
        print("Pipeline failed at skeleton generation")
        return

    # 2. Detail 생성
    detail = test_map_detail(skeleton)
    if detail is None:
        print("Pipeline failed at detail generation")
        return

    print("\n" + "=" * 50)
    print("Full pipeline completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Map Generator Test')
    parser.add_argument('--skeleton', action='store_true', help='Test skeleton generation only')
    parser.add_argument('--detail', action='store_true', help='Test detail generation only')
    parser.add_argument('--full', action='store_true', help='Test full pipeline')

    args = parser.parse_args()

    if args.skeleton:
        test_map_skeleton()
    elif args.detail:
        test_map_detail()
    elif args.full:
        test_full_pipeline()
    else:
        # 기본: 전체 파이프라인 테스트
        test_full_pipeline()
