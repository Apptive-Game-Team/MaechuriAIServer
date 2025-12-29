import json

from app.services.prompt.prompt_loader import PromptLoader
import re


class SuspectAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt = PromptLoader.load(
            "app/prompts/suspect/system.txt"
        )
        self.build_prompt = PromptLoader.load(
            "app/prompts/suspect/build.txt"
        )

    def generate(self, agent_input: dict) -> dict:
        prompt = self._build_prompt(agent_input)

        raw = self.llm.complete(
            system=self.system_prompt,
            user=prompt,
        )
        print("===========================================================")
        print(raw)
        print("===========================================================\n\n\n\n\n\n")
        json_text = self._extract_json(raw)

        return self._safe_json_load(json_text)

    def _build_prompt(self, agent_input: dict) -> str:
        return json.dumps({
            "input": agent_input,
            "instruction": self.build_prompt,
        }, ensure_ascii=False)

    def _extract_json(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError(
                f"LLM output is incomplete JSON:\n{text}"
            )

        return text[start:end + 1]

    def _safe_json_load(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 1차 복구: Python True/False/None → JSON
            repaired = (
                text.replace("True", "true")
                .replace("False", "false")
                .replace("None", "null")
            )

            return json.loads(repaired)
