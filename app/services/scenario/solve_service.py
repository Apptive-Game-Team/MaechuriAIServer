"""Solve Service for validating user solutions."""
import logging
import numpy as np
from typing import List

from app.services.llm.llm_client import LLMClient
from app.services.llm import ensure_langgraph_llm_client
from app.services.embedding.embedding_service import get_embedding_service
from app.services.agent.solve_validator import SolveValidator
from app.services.scenario.formatters import SolveFormatter
from app.db.repositories.scenario_repository import ScenarioRepository
from app.models.schemas.solve import ScenarioSolveResponse

logger = logging.getLogger(__name__)

# Configuration
SIMILARITY_THRESHOLD = 0.7


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
        self.llm_client = ensure_langgraph_llm_client(llm_client)
        self.embedding_service = get_embedding_service()
        self.solve_validator = SolveValidator(self.llm_client)
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
        culprit_match = SolveFormatter.check_culprit_match(
            expected_culprit_ids,
            submitted_culprit_ids
        )

        # 4. 범인이 틀리면 즉시 오답 처리
        if not culprit_match.is_match:
            logger.info(f"[Scenario {scenario_id}] Culprit mismatch - INCORRECT")
            return SolveFormatter.create_incorrect_response(
                scenario_id,
                culprit_match
            )

        # 5. Ground truth 문장 생성
        ground_truth = SolveFormatter.build_ground_truth_text(scenario_data)
        logger.debug(f"[Scenario {scenario_id}] Ground truth: {ground_truth}")

        # 6. 임베딩 유사도 계산
        similarity_score = self._calculate_similarity(ground_truth, user_solution)
        logger.info(f"[Scenario {scenario_id}] Similarity score: {similarity_score:.4f}")

        # 7. 유사도 기반 분기
        if similarity_score >= SIMILARITY_THRESHOLD:
            # 높은 유사도 → 정답 처리 (LLM 호출 안 함)
            reasoning_score = similarity_score * 100
            logger.info(f"[Scenario {scenario_id}] High similarity - skipping LLM")
            return SolveFormatter.create_response(
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
        return SolveFormatter.create_response(
            scenario_id=scenario_id,
            culprit_match=culprit_match,
            reasoning_score=float(validation_result.total_score),
            similarity_score=similarity_score,
            feedback=validation_result.feedback,
            hints=validation_result.missing_elements if validation_result.missing_elements else None
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts.

        Parameters
        ----------
        text1 : str
            First text (ground truth)
        text2 : str
            Second text (user solution)

        Returns
        -------
        float
            Cosine similarity (0.0 ~ 1.0)
        """
        embedding1 = self.embedding_service.embed_text(text1)
        embedding2 = self.embedding_service.embed_text(text2)

        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        return float(np.clip(similarity, 0.0, 1.0))
