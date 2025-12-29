class TruthModel:
    def __init__(self, is_lying: bool, hide_topics: list[str], lie_strategy: str):
        self.is_lying = is_lying
        self.hide_topics = hide_topics
        self.lie_strategy = lie_strategy

    def should_hide(self, topic: str) -> bool:
        # TODO: 이 녀석이 진실만 쳐 말하면 정답도 다 말할 거니까 거짓말 할 지 말 지
        pass