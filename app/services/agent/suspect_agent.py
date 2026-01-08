

class SuspectAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
        # TODO: Load chat-specific prompts here
        # self.system_prompt = PromptLoader.load("app/prompts/suspect/chat_system.txt")

    async def chat_generate(self,
                            suspect_personality: dict,
                            user_message: str,
                            history: dict) -> str:
        # TODO: Implement chat generation logic using self.llm
        return "테스트입니다"