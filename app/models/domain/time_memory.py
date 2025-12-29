from datetime import time

class TimeMemory:
    def __init__(self, anchors: list[dict], routines: list[dict]):
        self.anchors = anchors
        self.routines = routines

    # 정확하게 말할 수 있다면
    def has_exact_minute(self, t: time) -> bool:
        for a in self.anchors:
            if a["time"] == t.isoformat() and a["certainty"] == "high":
                return True
        return False

    # 만약 그 시간에 하는 게 없다면
    def find_routine(self, t: time) -> dict | None:
        for r in self.routines:
            if r["start"] <= t.isoformat() <= r["end"]:
                return r
        return None
