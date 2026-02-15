from typing import List, Dict, Any, Optional
from app.models.domain.fsm.interrogation import InterrogationState, AllowedMoves


class Suspect:
    def __init__(
            self,
            suspect_id: int,
            name: str,
            role: str,
            age: int,
            gender: str,
            description: str,
            is_culprit: bool,
            current_pressure: int,
            secrets: List[str],
            clue_seen: List[str],
            timeline: List[Dict[str, Any]],
            # New fields for chat
            time_memory: Optional[Dict[str, Any]] = None,
            observation: Optional[Dict[str, Any]] = None,
            answering_rule: Optional[Dict[str, Any]] = None,
            truth_model: Optional[Dict[str, Any]] = None,
            secrets_by_stage: Optional[Dict[str, List[str]]] = None,
            # Context fields (set after creation)
            incident_summary: str = "",
            primary_location: str = "",
    ):
        self.suspect_id = suspect_id
        self.name = name
        self.role = role
        self.age = age
        self.gender = gender
        self.description = description
        self.is_culprit = is_culprit
        self.current_pressure = current_pressure
        self.secrets = secrets
        self.clue_seen = clue_seen
        self.timeline = timeline

        # Chat-related fields
        self.time_memory = time_memory or {"routines": [], "anchors": []}
        self.observation = observation or {"can_see": [], "cannot_see": []}
        self.answering_rule = answering_rule or {
            "minute_precision_allowed": False,
            "unknown_reply_policy": "잘 모르겠습니다"
        }
        self.truth_model = truth_model or {"hide_topics": [], "lie_strategy": "deflect"}
        self.secrets_by_stage = secrets_by_stage or {
            "defensive": [],
            "cornered": [],
            "breakdown": [],
            "confession": []
        }

        # Context
        self.incident_summary = incident_summary
        self.primary_location = primary_location

    @classmethod
    def from_schema(cls, schema_data: dict, case_context: dict = None) -> "Suspect":
        """
        Create Suspect from SuspectSchema data.
        Optionally inject case_context for incident_summary and primary_location.
        """
        case_context = case_context or {}

        return cls(
            suspect_id=schema_data["suspect_id"],
            name=schema_data["name"],
            role=schema_data["role"],
            age=schema_data.get("age", 0),
            gender=schema_data.get("gender", "Unknown"),
            description=schema_data.get("description", ""),
            is_culprit=schema_data["is_culprit"],
            current_pressure=schema_data.get("current_pressure", 0),
            secrets=schema_data.get("secrets", []),
            clue_seen=schema_data.get("clue_seen", []),
            timeline=schema_data.get("timeline", []),
            # New fields
            time_memory=schema_data.get("time_memory"),
            observation=schema_data.get("observation"),
            answering_rule=schema_data.get("answering_rule"),
            truth_model=schema_data.get("truth_model"),
            secrets_by_stage=schema_data.get("secrets_by_stage"),
            # Context injection
            incident_summary=case_context.get("summary", ""),
            primary_location=case_context.get("primary_location", ""),
        )

    @classmethod
    def from_json(cls, data: dict) -> "Suspect":
        """Legacy method - use from_schema for new code."""
        return cls.from_schema(data)

    def to_personality_dict(self) -> Dict[str, Any]:
        """
        Convert to personality dict format for SuspectAgent.chat_generate().
        This is the format expected by chat_service.py.
        """
        return {
            # Basic info
            "name": self.name,
            "role": self.role,
            "age": self.age,
            "gender": self.gender,
            "description": self.description,

            # Context
            "incident_summary": self.incident_summary,
            "primary_location": self.primary_location,

            # Memory & Behavior
            "time_memory": self.time_memory,
            "observation": self.observation,
            "answering_rule": self.answering_rule,
            "truth_model": self.truth_model,

            # Secrets (FSM-ready)
            "secrets_by_stage": self.secrets_by_stage,

            # Clue tracking
            "clue_seen": [],  # Initialize empty, updated during interrogation

            # Interrogation state (initialized)
            "interrogation_state": {
                "state": InterrogationState.DEFENSIVE,
                "metrics": {
                    "pressure": self.current_pressure,
                    "contradictions": 0,
                    "clue_weight_seen": 0,
                    "trust_in_interrogator": 0
                },
                "allowed_moves": AllowedMoves.DEFENSIVE
            }
        }

    def get_revealed_secrets(self) -> List[str]:
        """
        Return secrets that are revealed based on current pressure.
        The secrets list is ordered from low pressure (defensive) to high pressure (confession).
        """
        if not self.secrets:
            return []

        count = len(self.secrets)
        step = 100 / count if count > 0 else 100
        reveal_count = int(self.current_pressure / step) + 1
        reveal_count = min(reveal_count, count)

        return self.secrets[:reveal_count]

    def update_pressure(self, amount: int) -> None:
        """Update pressure, clamping between 0 and 100."""
        self.current_pressure = max(0, min(100, self.current_pressure + amount))
