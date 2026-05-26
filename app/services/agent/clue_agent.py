from app.services.llm import ensure_langgraph_llm_client
from app.services.prompt.prompt_loader import PromptLoader


class ClueAgent:
    def __init__(self, llm_client):
        self.llm = ensure_langgraph_llm_client(llm_client)
        self.system_prompt_template = PromptLoader.load("app/prompts/clue/chat_system.txt")

    async def chat_generate(
        self,
        clue_info: dict,
        user_message: str,
    ) -> str:
        """
        증거 분석 대화 생성

        Args:
            clue_info: 증거 정보 (name, description, etc.) + optional rag_context
            user_message: 유저 메시지
        """
        # RAG 컨텍스트 추출
        rag_context = clue_info.get("rag_context", "")

        # 시스템 프롬프트 구성
        system_prompt = self.system_prompt_template.format(
            name=clue_info.get("name", "알 수 없음"),
            found_at=clue_info.get("found_at", "알 수 없음"),
            description=clue_info.get("description", "설명 없음"),
            logic_explanation=clue_info.get("logic_explanation", "논리적 설명 없음"),
            decoded_answer=clue_info.get("decoded_answer", "분석 결과 없음"),
            is_red_herring=clue_info.get("is_red_herring", False),
            rag_context=rag_context
        )

        # LLM 호출
        response = self.llm.complete(
            system=system_prompt,
            user=user_message
        )

        return response
