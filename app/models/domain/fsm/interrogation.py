from enum import Enum

class InterrogationState(str, Enum):
    DEFENSIVE = "DEFENSIVE"
    CORNERED = "CORNERED"
    BREAKDOWN = "BREAKDOWN"
    CONFESSION = "CONFESSION"

class AllowedMoves:
    DEFENSIVE = ["deny", "deflect", "question_back"]
    CORNERED = ["deflect", "partial_admit", "hesitate"]
    BREAKDOWN = ["silence", "cry", "partial_confession", "beg"]
    CONFESSION = ["full_confession", "reveal_method", "reveal_motive"]

    @staticmethod
    def get_moves(state: InterrogationState) -> list[str]:
        if state == InterrogationState.DEFENSIVE:
            return AllowedMoves.DEFENSIVE
        if state == InterrogationState.CORNERED:
            return AllowedMoves.CORNERED
        if state == InterrogationState.BREAKDOWN:
            return AllowedMoves.BREAKDOWN
        if state == InterrogationState.CONFESSION:
            return AllowedMoves.CONFESSION
        return []
