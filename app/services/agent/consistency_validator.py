from dataclasses import dataclass
from typing import List
from pydantic import BaseModel

import app.models.schemas
from app.models.schemas import SuspectGenerationRequest


@dataclass
class ValidationIssue:
    code: str
    message: str
    suspect_id: str | None = None

@dataclass
class ValidationResult:
    is_valid: bool
    issues: List[ValidationIssue]

class ConsistencyValidator:

    # TODO: 객체당 설정 필요 시 스태틱 해제 필요
    # TODO: self 추가 필요
    @staticmethod
    def validate_pre_json(
            request: SuspectGenerationRequest
    ) -> ValidationResult :
        issues: List[ValidationIssue] = []

        case = request.case_context
        world = request.world_context
        truth = request.ground_truth
        config = request.generation_config

        if not (
            case.incident_time.start
            <= truth.crime_time_range.start
            <= truth.crime_time_range.end
            <= case.incident_time.end
        ):
            issues.append(
                ValidationIssue(
                    code="TIME_RANGE_INVALID",
                    message="crime_time_range must be within incident_time",
                )
            )

        if truth.crime_location not in world.locations:
            issues.append(
                ValidationIssue(
                   code="INVALID_CRIME_LOCATION",
                    message="crime_location not in world.locations",
                )
            )

        for ev in truth.required_evidence:
            if ev.type not in world.evidence_types:
                issues.append(
                    ValidationIssue(
                        code="UNKNOWN_EVIDENCE_TYPE",
                        message=f"evidence_type `{ev.type}` not allowed",
                    )
                )

        if config.suspect_count < truth.culprit_count:
            issues.append(
                ValidationIssue(
                    code="INSUFFICIENT_SUSPECT_COUNT",
                    message="suspect_count < culprit_count",
                )
            )

        return ValidationResult(
            is_valid= len(issues) == 0,
            issues = issues,
        )

    @staticmethod
    def validate_post_json(post_json: dict) -> ValidationResult:
        issues: List[ValidationIssue] = []

        suspects = post_json.get("suspects", [])
        if not suspects:
            issues.append(
                ValidationIssue(
                    code="NO_SUSPECTS",
                    message="post_json contains no suspects",
                )
            )
            return ValidationResult(False, issues)

        # 1. suspect_id 중복 검사
        seen_ids = set()
        for s in suspects:
            sid = s.get("suspect_id")
            if sid in seen_ids:
                issues.append(
                    ValidationIssue(
                        code="DUPLICATE_SUSPECT_ID",
                        message=f"duplicate suspect_id '{sid}'",
                        suspect_id=sid,
                    )
                )
            seen_ids.add(sid)

        # 2. 시간 루틴 start <= end
        for s in suspects:
            sid = s.get("suspect_id")
            routines = s.get("time_memory", {}).get("routines", [])

            for r in routines:
                if r["start"] > r["end"]:
                    issues.append(
                        ValidationIssue(
                            code="INVALID_ROUTINE_TIME",
                            message="routine start > end",
                            suspect_id=sid,
                        )
                    )

        # 3. 같은 용의자 루틴 겹침 검사
        for s in suspects:
            sid = s.get("suspect_id")
            routines = s.get("time_memory", {}).get("routines", [])

            sorted_r = sorted(routines, key=lambda r: r["start"])
            for i in range(len(sorted_r) - 1):
                if sorted_r[i]["end"] > sorted_r[i + 1]["start"]:
                    issues.append(
                        ValidationIssue(
                            code="ROUTINE_OVERLAP",
                            message="overlapping routines detected",
                            suspect_id=sid,
                        )
                    )

        # 4. cannot_see + 직접 관측 충돌 (단순)
        for s in suspects:
            sid = s.get("suspect_id")

            observations = s.get("observation", [])
            cannot_see = set()

            for o in observations:
                for loc in o.get("cannot_see", []):
                    cannot_see.add(loc)

            anchors = s.get("time_memory", {}).get("anchors", [])

            for a in anchors:
                loc = a.get("location")
                if loc and loc in cannot_see:
                    issues.append(
                        ValidationIssue(
                            code="OBSERVATION_CONFLICT",
                            message=f"anchor at unseen location '{loc}'",
                            suspect_id=sid,
                        )
                    )

        # 5. 전원 완벽 알리바이 방지 (매우 단순 MVP)
        # 사건 시간대에 'uncertain' 구간이 최소 1명 있어야 함
        uncertain_exists = False
        for s in suspects:
            routines = s.get("time_memory", {}).get("routines", [])
            for r in routines:
                if r.get("certainty") in ("low", "medium"):
                    uncertain_exists = True
                    break

        if not uncertain_exists:
            issues.append(
                ValidationIssue(
                    code="PERFECT_ALIBI_FOR_ALL",
                    message="all suspects have perfect alibi",
                )
            )

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
        )