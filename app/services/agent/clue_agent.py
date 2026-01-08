

class ClueAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
        # TODO: Load chat-specific prompts here
        # self.system_prompt = PromptLoader.load("app/prompts/clue/chat_system.txt")

    async def chat_generate(self,
                            clue_info: dict,
                            user_message: str,
                            history: dict) -> str:
        # TODO: Implement chat generation logic using self.llm
        return "증거 분석 결과입니다."