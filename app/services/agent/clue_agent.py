from app.services.prompt.prompt_loader import PromptLoader


class ClueAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt_template = PromptLoader.load("app/prompts/clue/chat_system.txt")

    async def chat_generate(
        self,
        clue_info: dict,
        user_message: str,
        history: list
    ) -> str:
        """
        증거 분석 대화 생성
        """
        # 히스토리 포맷팅
        history_str = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in history])

        # 시스템 프롬프트 구성
        system_prompt = self.system_prompt_template.format(
            name=clue_info.get("name", "알 수 없음"),
            found_at=clue_info.get("found_at", "알 수 없음"),
            description=clue_info.get("description", "설명 없음"),
            logic_explanation=clue_info.get("logic_explanation", "논리적 설명 없음"),
            decoded_answer=clue_info.get("decoded_answer", "분석 결과 없음"),
            is_red_herring=clue_info.get("is_red_herring", False),
            chat_history=history_str
        )

        # LLM 호출
        # LLMClient.complete는 동기 함수이므로 그대로 호출하거나, 필요시 run_in_executor 사용
        response = self.llm.complete(
            system=system_prompt,
            user=user_message
        )

        return response