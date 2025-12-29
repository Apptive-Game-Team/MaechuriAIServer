from app.models.domain import Suspect

class NPCChatService:
    def __init__(self, repository):
        self.repository = repository