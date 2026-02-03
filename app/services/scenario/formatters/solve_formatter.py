"""Formatter and helper functions for solve service."""
from typing import List, Optional

from app.models.schemas.solve import (
    SolveResultStatus,
    CulpritMatchResult,
    ScenarioSolveResponse
)

# Configuration
PASSING_SCORE = 70
CULPRIT_WEIGHT = 0.4
REASONING_WEIGHT = 0.6


class SolveFormatter:
    """Formatter class for solve-related operations."""

    @staticmethod
    def check_culprit_match(
        expected: List[int],
        submitted: List[int]
    ) -> CulpritMatchResult:
        """Check if culprit IDs match.

        Parameters
        ----------
        expected : List[int]
            Expected culprit ID list
        submitted : List[int]
            Submitted culprit ID list

        Returns
        -------
        CulpritMatchResult
            Match result
        """
        expected_set = set(expected)
        submitted_set = set(submitted)

        is_match = expected_set == submitted_set

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

    @staticmethod
    def build_ground_truth_text(scenario_data: dict) -> str:
        """Build ground truth text from scenario data.

        Parameters
        ----------
        scenario_data : dict
            Scenario data

        Returns
        -------
        str
            Ground truth text including culprit name, motive, method, time, location
        """
        ground_truth_detail = scenario_data["ground_truth_detail"]
        suspects = scenario_data["suspects"]

        culprit_ids = ground_truth_detail["culprit_ids"]
        culprits = [s for s in suspects if s["suspect_id"] in culprit_ids]

        if not culprits:
            raise ValueError("No culprit found in scenario data")

        culprit_names = ", ".join([c["name"] for c in culprits])

        motives = [c.get("motive", "") for c in culprits if c.get("motive")]
        motive_text = "; ".join(motives) if motives else "알 수 없음"

        method = ground_truth_detail.get("method", "알 수 없음")

        crime_time = ground_truth_detail.get("crime_time_range", {})
        time_start = crime_time.get("start", "")
        time_end = crime_time.get("end", "")
        if time_start and time_end:
            time_text = f"{time_start} ~ {time_end}"
        elif time_start:
            time_text = str(time_start)
        else:
            time_text = "알 수 없음"

        crime_location = ground_truth_detail.get("crime_location", "알 수 없음")

        ground_truth = (
            f"범인: {culprit_names}. "
            f"동기: {motive_text}. "
            f"수법: {method}. "
            f"범행 시간: {time_text}. "
            f"범행 장소: {crime_location}."
        )

        return ground_truth

    @staticmethod
    def create_incorrect_response(
        scenario_id: int,
        culprit_match: CulpritMatchResult
    ) -> ScenarioSolveResponse:
        """Create response for incorrect culprit.

        Parameters
        ----------
        scenario_id : int
            Scenario ID
        culprit_match : CulpritMatchResult
            Culprit match result

        Returns
        -------
        ScenarioSolveResponse
            Incorrect response
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

    @staticmethod
    def create_response(
        scenario_id: int,
        culprit_match: CulpritMatchResult,
        reasoning_score: float,
        similarity_score: float,
        feedback: str,
        hints: Optional[List[str]]
    ) -> ScenarioSolveResponse:
        """Create validation result response.

        Parameters
        ----------
        scenario_id : int
            Scenario ID
        culprit_match : CulpritMatchResult
            Culprit match result
        reasoning_score : float
            Reasoning score (0~100)
        similarity_score : float
            Similarity score (0~1)
        feedback : str
            Feedback message
        hints : Optional[List[str]]
            Hint list

        Returns
        -------
        ScenarioSolveResponse
            Validation result response
        """
        culprit_score = 100.0 if culprit_match.is_match else 0.0
        total_score = (culprit_score * CULPRIT_WEIGHT) + (reasoning_score * REASONING_WEIGHT)

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
