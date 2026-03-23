from typing import TypeVar, Callable
import json
import logging
import time
from pydantic import BaseModel, ValidationError

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)


class JSONParseRetry:
    """JSON 파싱 실패 시 재시도 로직"""

    BASE_OUTPUT_TOKENS = 8192

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_seconds: float = 2.0,
        backoff_multiplier: float = 1.0  # 1.0 = 일정, 2.0 = 지수
    ):
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.backoff_multiplier = backoff_multiplier

    def parse_with_retry(
        self,
        parser_func: Callable[[], T],
        schema_name: str,
        generator=None,
    ) -> T | None:
        """
        JSON 파싱 함수를 재시도와 함께 실행

        Parameters
        ----------
        parser_func : Callable
            JSON 파싱을 수행하는 함수 (LLM 호출 → 파싱)
        schema_name : str
            로깅용 스키마 이름 (예: "ScenarioSkeleton")

        Returns
        -------
        T | None
            파싱 성공 시 결과 객체, 모든 시도 실패 시 None
        """
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                # Escalate max_output_tokens on each attempt: 8192 → 16384 → 32768 ...
                if generator is not None:
                    generator._max_output_tokens = self.BASE_OUTPUT_TOKENS * (2 ** (attempt - 1))
                    logger.info(
                        f"[{schema_name}] max_output_tokens={generator._max_output_tokens}"
                    )

                logger.info(f"[{schema_name}] Parsing attempt {attempt}/{self.max_attempts}")
                result = parser_func()
                logger.info(f"[{schema_name}] ✅ Success on attempt {attempt}")
                return result

            except json.JSONDecodeError as e:
                # safe_json_load() 실패 (JSON 파싱 불가)
                logger.warning(f"[{schema_name}] ❌ Attempt {attempt} - JSONDecodeError: {e}")
                last_error = e

            except ValueError as e:
                # extract_json() 실패 (JSON 경계 못찾음)
                logger.warning(f"[{schema_name}] ❌ Attempt {attempt} - ValueError: {e}")
                last_error = e
            except ValidationError as e:
                # Pydantic 검증 실패 (스키마 불일치)
                error_count = len(e.errors())
                logger.warning(f"[{schema_name}] ❌ Attempt {attempt} - ValidationError: {error_count} errors")
                for err in e.errors()[:3]:  # 처음 3개만 로깅
                    logger.warning(f"  - {err['loc']}: {err['msg']}")
                last_error = e

            except Exception as e:
                # 기타 예상치 못한 에러
                logger.error(f"[{schema_name}] ❌ Attempt {attempt} - Unexpected: {type(e).__name__}: {e}")
                last_error = e

            # 재시도 대기
            if attempt < self.max_attempts:
                wait_time = self.backoff_seconds * (self.backoff_multiplier ** (attempt - 1))
                logger.info(f"[{schema_name}] Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)

        # 모든 시도 실패 — reset token override
        if generator is not None:
            generator._max_output_tokens = None
        logger.error(f"[{schema_name}] ❌ All {self.max_attempts} attempts failed. Last error: {last_error}")
        return None
