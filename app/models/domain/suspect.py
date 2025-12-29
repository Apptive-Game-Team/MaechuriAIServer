from datetime import time
import re

from .answering_rule import AnsweringRule
from .dialogue_state import DialogueState
from .observation import Observation
from .time_memory import TimeMemory
from .truth_model import TruthModel


class Suspect:
    def __init__(
            self,
            suspect_id: str, # TODO: 번호로 할 것인지?
            time_memory: TimeMemory,
            observation: Observation,
            answering_rule: AnsweringRule,
            truth_model: TruthModel,
            dialogue_state: DialogueState,
    ):
        self.suspect_id = suspect_id
        self.time_memory = time_memory
        self.observation = observation
        self.answering_rule = answering_rule
        self.truth_model = truth_model
        self.dialogue_state = dialogue_state

    @classmethod
    def from_json(cls, data: dict) -> "Suspect":
        return cls(
            suspect_id=data["suspect_id"],
            time_memory=TimeMemory(
                anchors=data["time_memory"]["anchors"],
                routines=data["time_memory"]["routines"],
            ),
            observation=Observation(
                can_see=data["observation"]["can_see"],
                cannot_see=data["observation"]["cannot_see"],
                noise_effect=data["observation"]["noise_effect"],
            ),
            answering_rule=AnsweringRule(
                minute_precision_allowed=data["answering_rule"]["minute_precision_allowed"],
                unknown_reply_policy=data["answering_rule"]["unknown_reply_policy"],
                out_of_incident_time_policy=data["answering_rule"]["out_of_incident_time_policy"],
            ),
            truth_model=TruthModel(
                is_lying=data["truth_model"]["is_lying"],
                hide_topics=data["truth_model"]["hide_topics"],
                lie_strategy=data["truth_model"]["lie_strategy"],
            ),
            dialogue_state=DialogueState(),
        )


    # TODO: 대사 관련 수정. 시간 수정
    def answer(self, user_message: str) -> str:
        t_str = self._extract_time(user_message)
        if not t_str:
            return "그건 잘 모르겠네요."

        if t_str in self.dialogue_state.asked_times:
            return "아까 말씀드린 것과 같아요."

        self.dialogue_state.asked_times.add(t_str)
        t = time.fromisoformat(t_str)

        if self.answering_rule.minute_precision_allowed:
            if self.time_memory.has_exact_minute(t):
                return f"{t_str}쯤에는 분명히 기억나요."

        routine = self.time_memory.find_routine(t)
        if routine:
            return (
                f"정확한 시간은 기억 안 나지만 "
                f"{routine['activity']} 하고 있었어요."
            )

        return "그 시간대 일은 잘 기억나지 않네요."

    def _extract_time(self, message: str) -> str | None:
        match = re.search(r'(\d{1,2})시\s*(\d{1,2})분', message)
        if match:
            h, m = match.groups()
            return f"{int(h):02d}:{int(m):02d}"

        match = re.search(r'(\d{2}:\d{2})', message)
        if match:
            return match.group(1)

        return None
