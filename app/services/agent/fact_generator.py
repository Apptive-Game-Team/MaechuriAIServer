import json

from app.core.utils import extract_json, safe_json_load
from app.models.schemas.fact_generation import GeneratedGlobalFact
from app.services.llm import ensure_langgraph_llm_client
from app.services.llm.llm_client import LLMClient


FACT_GENERATION_SYSTEM = """
You create one canonical global fact for a Korean mystery detective game.

Rules:
- Read the full scenario context before deciding the fact.
- The new fact must not contradict the incident, suspects, clues, solve logic,
  existing facts, locations, or prior generated state.
- The fact should answer only the suspect self-info uncertainty being asked.
- Prefer mundane, globally consistent details over dramatic new plot twists.
- Do not create culprit proof, confession, murder method, or clue logic unless
  the existing scenario already supports it.
- Write the fact in Korean.
""".strip()


class FactGenerator:
    """LLM-backed generator for canonical scenario facts."""

    def __init__(self, llm_client: LLMClient):
        self.llm = ensure_langgraph_llm_client(llm_client)

    async def agenerate_global_fact(
        self,
        *,
        scenario: dict,
        suspect: dict,
        wonder: str,
    ) -> GeneratedGlobalFact:
        user_payload = {
            "wonder": wonder,
            "suspect": suspect,
            "scenario": scenario,
        }
        raw = await self.llm.acomplete(
            system=FACT_GENERATION_SYSTEM,
            user=json.dumps(user_payload, ensure_ascii=False, indent=2),
            response_schema=GeneratedGlobalFact.model_json_schema(),
        )
        json_text = extract_json(raw)
        data = safe_json_load(json_text)
        return GeneratedGlobalFact.model_validate(data)
