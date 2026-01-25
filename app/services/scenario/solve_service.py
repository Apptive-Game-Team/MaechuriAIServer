"""Solve Service for validating user solutions."""
import logging
import numpy as np
from typing import List, Optional

from app.services.llm.llm_client import LLMClient
from app.services.embedding.embedding_service import get_embedding_service
from app.services.agent.solve_validator import SolveValidator
from app.db.repositories.scenario_repository import ScenarioRepository
from app.models.schemas.solve import (
    SolveResultStatus,
    CulpritMatchResult,
    ScenarioSolveResponse
)

logger = logging.getLogger(__name__)

# Configuration
SIMILARITY_THRESHOLD = 0.7
PASSING_SCORE = 70
CULPRIT_WEIGHT = 0.4
REASONING_WEIGHT = 0.6


class SolveService:
    """
    시나리오 추리 검증 서비스.

    검증 흐름:
    1. 범인 ID 검증 (필수 - 틀리면 즉시 오답)
    2. Ground truth 문장 생성
    3. 임베딩 유사도 계산 (BGE-M3)
    4. 유사도 >= 0.7 → 정답
    5. 유사도 < 0.7 → LLM 추가 검증
    6. 최종 점수 계산 및 응답
    """

    def __init__(self, llm_client: LLMClient):
        """
        Initialize SolveService.

        Parameters
        ----------
        llm_client : LLMClient
            LLM client for validation
        """
        self.llm_client = llm_client
        self.embedding_service = get_embedding_service()
        self.solve_validator = SolveValidator(llm_client)
        self.repository = ScenarioRepository()

    async def solve(
        self,
        scenario_id: int,
        submitted_culprit_ids: List[int],
        user_solution: str
    ) -> ScenarioSolveResponse:
        """
        유저의 추리를 검증하고 결과 반환.

        Parameters
        ----------
        scenario_id : int
            시나리오 ID
        submitted_culprit_ids : List[int]
            유저가 제출한 범인 ID 목록
        user_solution : str
            유저의 추리 내용

        Returns
        -------
        ScenarioSolveResponse
            검증 결과
        """
        logger.info(f"[Scenario {scenario_id}] Processing solve request")

        # 1. 시나리오 데이터 조회
        scenario_data = await self.repository.get_scenario_by_id(scenario_id)
        if not scenario_data:
            raise ValueError(f"Scenario {scenario_id} not found")

        # 2. 정답 범인 ID 추출
        expected_culprit_ids = scenario_data["ground_truth_detail"]["culprit_ids"]

        # 3. 범인 ID 검증
        culprit_match = self._check_culprit_match(
            expected_culprit_ids,
            submitted_culprit_ids
        )

        # 4. 범인이 틀리면 즉시 오답 처리
        if not culprit_match.is_match:
            logger.info(f"[Scenario {scenario_id}] Culprit mismatch - INCORRECT")
            return self._create_incorrect_response(
                scenario_id,
                culprit_match
            )

        # 5. Ground truth 문장 생성
        ground_truth = self._build_ground_truth_text(scenario_data)
        logger.debug(f"[Scenario {scenario_id}] Ground truth: {ground_truth}")

        # 6. 임베딩 유사도 계산
        similarity_score = self._calculate_similarity(ground_truth, user_solution)
        logger.info(f"[Scenario {scenario_id}] Similarity score: {similarity_score:.4f}")

        # 7. 유사도 기반 분기
        if similarity_score >= SIMILARITY_THRESHOLD:
            # 높은 유사도 → 정답 처리 (LLM 호출 안 함)
            reasoning_score = similarity_score * 100
            logger.info(f"[Scenario {scenario_id}] High similarity - skipping LLM")
            return self._create_response(
                scenario_id=scenario_id,
                culprit_match=culprit_match,
                reasoning_score=reasoning_score,
                similarity_score=similarity_score,
                feedback="추리가 정확합니다. 핵심 요소를 모두 파악했습니다.",
                hints=None
            )

        # 8. 낮은 유사도 → LLM 추가 검증
        logger.info(f"[Scenario {scenario_id}] Low similarity - using LLM validation")
        validation_result = self.solve_validator.validate(
            ground_truth=ground_truth,
            user_solution=user_solution
        )

        # 9. 최종 응답 생성
        return self._create_response(
            scenario_id=scenario_id,
            culprit_match=culprit_match,
            reasoning_score=float(validation_result.total_score),
            similarity_score=similarity_score,
            feedback=validation_result.feedback,
            hints=validation_result.missing_elements if validation_result.missing_elements else None
        )

    def _check_culprit_match(
        self,
        expected: List[int],
        submitted: List[int]
    ) -> CulpritMatchResult:
        """
        범인 ID 일치 여부 확인.

        Parameters
        ----------
        expected : List[int]
            정답 범인 ID 목록
        submitted : List[int]
            제출된 범인 ID 목록

        Returns
        -------
        CulpritMatchResult
            일치 결과
        """
        expected_set = set(expected)
        submitted_set = set(submitted)

        # 완전 일치 확인
        is_match = expected_set == submitted_set

        # 일치율 계산 (교집합 / 합집합)
        if not expected_set and not submitted_set:
            match_rate = 1.0
        elif not expected_set or not submitted_set:
            match_rate = 0.0
        else:
            intersection = len(expected_set & submitted_set)
            union = len(expected_set | submitted_set)
            match_rate = intersection / union

        return CulpritMatchResult(
            expected=expected,
            submitted=submitted,
            is_match=is_match,
            match_rate=match_rate
        )

    def _build_ground_truth_text(self, scenario_data: dict) -> str:
        """
        Ground truth 문장 생성.

        Parameters
        ----------
        scenario_data : dict
            시나리오 데이터

        Returns
        -------
        str
            범인명, 동기, 수법, 시간, 장소를 포함한 정답 문장
        """
        ground_truth_detail = scenario_data["ground_truth_detail"]
        suspects = scenario_data["suspects"]

        # 범인 정보 추출
        culprit_ids = ground_truth_detail["culprit_ids"]
        culprits = [s for s in suspects if s["suspect_id"] in culprit_ids]

        if not culprits:
            raise ValueError("No culprit found in scenario data")

        # 범인 이름들
        culprit_names = ", ".join([c["name"] for c in culprits])

        # 동기 (첫 번째 범인의 동기 사용, 또는 모든 범인 동기 결합)
        motives = [c.get("motive", "") for c in culprits if c.get("motive")]
        motive_text = "; ".join(motives) if motives else "알 수 없음"

        # 수법
        method = ground_truth_detail.get("method", "알 수 없음")

        # 시간
        crime_time = ground_truth_detail.get("crime_time_range", {})
        time_start = crime_time.get("start", "")
        time_end = crime_time.get("end", "")
        if time_start and time_end:
            time_text = f"{time_start} ~ {time_end}"
        elif time_start:
            time_text = str(time_start)
        else:
            time_text = "알 수 없음"

        # 장소
        crime_location = ground_truth_detail.get("crime_location", "알 수 없음")

        # 문장 조합
        ground_truth = (
            f"범인: {culprit_names}. "
            f"동기: {motive_text}. "
            f"수법: {method}. "
            f"범행 시간: {time_text}. "
            f"범행 장소: {crime_location}."
        )

        return ground_truth

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        두 텍스트 간 코사인 유사도 계산.

        Parameters
        ----------
        text1 : str
            첫 번째 텍스트 (ground truth)
        text2 : str
            두 번째 텍스트 (user solution)

        Returns
        -------
        float
            코사인 유사도 (0.0 ~ 1.0)
        """
        embedding1 = self.embedding_service.embed_text(text1)
        embedding2 = self.embedding_service.embed_text(text2)

        # numpy 배열로 변환
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # 코사인 유사도 계산
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # 0~1 범위로 클리핑
        return float(np.clip(similarity, 0.0, 1.0))

    def _create_incorrect_response(
        self,
        scenario_id: int,
        culprit_match: CulpritMatchResult
    ) -> ScenarioSolveResponse:
        """
        범인 오답 시 응답 생성.

        Parameters
        ----------
        scenario_id : int
            시나리오 ID
        culprit_match : CulpritMatchResult
            범인 매칭 결과

        Returns
        -------
        ScenarioSolveResponse
            오답 응답
        """
        return ScenarioSolveResponse(
            scenario_id=scenario_id,
            status=SolveResultStatus.INCORRECT,
            success=False,
            culprit_score=0.0,
            reasoning_score=0.0,
            total_score=0.0,
            culprit_match=culprit_match,
            similarity_score=None,
            message="범인을 잘못 지목했습니다.",
            feedback="제출한 범인이 정답과 일치하지 않습니다. 증거와 용의자들의 진술을 다시 검토해보세요.",
            hints=["용의자들의 알리바이를 다시 확인해보세요.", "핵심 증거가 누구를 가리키고 있는지 생각해보세요."]
        )

    def _create_response(
        self,
        scenario_id: int,
        culprit_match: CulpritMatchResult,
        reasoning_score: float,
        similarity_score: float,
        feedback: str,
        hints: Optional[List[str]]
    ) -> ScenarioSolveResponse:
        """
        검증 결과 응답 생성.

        Parameters
        ----------
        scenario_id : int
            시나리오 ID
        culprit_match : CulpritMatchResult
            범인 매칭 결과
        reasoning_score : float
            추리 점수 (0~100)
        similarity_score : float
            유사도 점수 (0~1)
        feedback : str
            피드백 메시지
        hints : Optional[List[str]]
            힌트 목록

        Returns
        -------
        ScenarioSolveResponse
            검증 결과 응답
        """
        # 점수 계산
        culprit_score = 100.0 if culprit_match.is_match else 0.0
        total_score = (culprit_score * CULPRIT_WEIGHT) + (reasoning_score * REASONING_WEIGHT)

        # 상태 결정
        if reasoning_score >= PASSING_SCORE:
            status = SolveResultStatus.CORRECT
            success = True
            message = "축하합니다! 정확한 추리입니다."
        else:
            status = SolveResultStatus.PARTIAL
            success = False
            message = "범인은 맞았지만, 추리가 완전하지 않습니다."

        return ScenarioSolveResponse(
            scenario_id=scenario_id,
            status=status,
            success=success,
            culprit_score=culprit_score,
            reasoning_score=reasoning_score,
            total_score=total_score,
            culprit_match=culprit_match,
            similarity_score=similarity_score,
            message=message,
            feedback=feedback,
            hints=hints
        )
