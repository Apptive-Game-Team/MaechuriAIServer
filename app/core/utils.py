import json
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def extract_json(text: str) -> str:
    """
    Extracts the first JSON object found between '{' and '}'.
    """
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            f"LLM output is incomplete JSON:\n{text}"
        )

    return text[start:end + 1]


def safe_json_load(json_str: str) -> Dict[str, Any]:
    """
    JSON 문자열을 로드하며, 일반적인 LLM 출력 오류를 자동 복구

    복구 패턴:
    1. Python boolean/None → JSON (True→true, False→false, None→null)
    2. Trailing comma 제거
    3. 주석 제거 (// 및 /* */)
    4. 불필요한 줄바꿈 정리

    Parameters
    ----------
    json_str : str
        JSON 문자열

    Returns
    -------
    Dict[str, Any]
        파싱된 JSON 객체

    Raises
    ------
    json.JSONDecodeError
        복구 시도 후에도 파싱 실패 시
    """
    try:
        # 1차 시도: 그대로 파싱
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.debug(f"Initial JSON parse failed: {e}. Attempting repair...")

        # 복구 시도
        repaired = json_str

        # 1. Python → JSON 변환
        repaired = repaired.replace("True", "true")
        repaired = repaired.replace("False", "false")
        repaired = repaired.replace("None", "null")

        # 2. 주석 제거 (// 스타일)
        repaired = re.sub(r'//.*?$', '', repaired, flags=re.MULTILINE)

        # 3. 주석 제거 (/* */ 스타일)
        repaired = re.sub(r'/\*.*?\*/', '', repaired, flags=re.DOTALL)

        # 4. Trailing comma 제거 (배열/객체 끝)
        repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)

        # 5. 불필요한 공백/줄바꿈 정리
        repaired = repaired.strip()

        try:
            # 2차 시도: 복구 후 파싱
            result = json.loads(repaired)
            logger.info("✅ JSON repair successful")
            return result
        except json.JSONDecodeError as e2:
            logger.error(f"❌ JSON repair failed: {e2}")
            logger.debug(f"Original: {json_str[:200]}...")
            logger.debug(f"Repaired: {repaired[:200]}...")
            raise  # 복구 실패 시 원본 에러 전파