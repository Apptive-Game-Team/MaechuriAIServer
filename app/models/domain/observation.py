class Observation:
    def __init__(self, can_see: list[str], cannot_see: list[str], noise_effect: str):
        self.can_see = can_see
        self.cannot_see = cannot_see
        self.noise_effect = noise_effect

    def can_observe(self, location: str) -> bool:
        return location in self.can_see