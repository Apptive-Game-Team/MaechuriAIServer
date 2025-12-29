class DialogueState:
    # stateless한 웹 특성상 기억을 유지하기 위한 클래스
    def __init__(self):
        self.asked_times: set[str] = set()