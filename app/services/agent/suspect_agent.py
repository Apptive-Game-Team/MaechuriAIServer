import json

from app.core.utils import extract_json, safe_json_load
from app.services.prompt.prompt_loader import PromptLoader
class SuspectAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt = PromptLoader.load(
            "app/prompts/suspect/system.txt"
        )
        self.build_prompt = PromptLoader.load(
            "app/prompts/suspect/build.txt"
        )
    async def generate(self, agent_input: dict) -> dict:
        prompt = self._build_prompt(agent_input)

        raw = self.llm.complete(
            system=self.system_prompt,
            user=prompt,
        )
        json_text = extract_json(raw)

        return safe_json_load(json_text)

    async def chat_generate(self,
                      suspect_personality: dict,
                      previous_chat: str,
                      user_message: str) -> dict:
        pass

    def _build_prompt(self, agent_input: dict) -> str:
        return json.dumps({
            "input": agent_input,
            "instruction": self.build_prompt,
        }, ensure_ascii=False)
