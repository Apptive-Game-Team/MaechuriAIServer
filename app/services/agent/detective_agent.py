"""Detective agent for general chat - answers questions about the case."""
from typing import Optional, List
from app.services.prompt.prompt_loader import PromptLoader


class DetectiveAgent:
    """형사(조력자) 역할 에이전트.

    사건에 대한 전반적인 질문에 답변합니다.
    - 사건 개요, 시간, 장소
    - 용의자 정보 (공개 가능한 것만)
    - 단서 분석 (clue context 포함 시)
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.prompt_template = PromptLoader.load(
            "app/prompts/detective/chat_system.txt"
        )

    async def generate_response(
        self,
        user_message: str,
        rag_context: str,
        history_context: str = "",
        clue_infos: Optional[List[dict]] = None
    ) -> str:
        """
        형사의 응답 생성

        Args:
            user_message: 유저 메시지
            rag_context: RAG로 검색된 컨텍스트 (사건 정보, 용의자 등)
            history_context: RAG로 검색된 관련 대화 히스토리 (문자열)
            clue_infos: 참조된 단서 정보 목록 (있으면 컨텍스트에 포함)

        Returns:
            str: 형사의 응답
        """
        # 히스토리 포맷팅
        history_str = history_context if history_context else "(대화 시작)"

        # 단서 컨텍스트 구성
        clue_context = self._build_clue_context(clue_infos)

        # 시스템 프롬프트 구성
        system_prompt = self.prompt_template.format(
            rag_context=rag_context if rag_context else "(사건 정보 없음)",
            clue_context=clue_context,
            chat_history=history_str
        )

        # LLM 호출
        response = self.llm.complete(
            system=system_prompt,
            user=user_message
        )

        return response

    def _build_clue_context(self, clue_infos: Optional[List[dict]]) -> str:
        """단서 정보를 컨텍스트 문자열로 변환"""
        if not clue_infos:
            return "(현재 분석 중인 증거 없음)"

        parts = []
        for clue in clue_infos:
            clue_str = f"""[증거: {clue.get('name', '알 수 없음')}]
- 발견 장소: {clue.get('found_at', '알 수 없음')}
- 외관/설명: {clue.get('description', '설명 없음')}
- 해석된 의미: {clue.get('decoded_answer', '분석 결과 없음')}
- 주의: {'이 증거는 수사에 혼란을 줄 수 있음' if clue.get('is_red_herring') else ''}"""
            parts.append(clue_str)

        return "\n\n".join(parts)
