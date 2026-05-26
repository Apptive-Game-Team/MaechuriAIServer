import json
import logging
import time
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from app.core.utils import extract_json, safe_json_load
from app.services.llm import ensure_langgraph_llm_client

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseGenerator:
    def __init__(self, llm_client, system_prompt: str):
        self.llm = ensure_langgraph_llm_client(llm_client)
        self.system_prompt = system_prompt
        self._max_output_tokens: int | None = None

    def _generate(
        self,
        user_input: dict | str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        max_output_tokens: int | None = None,
    ) -> T:
        """Generate response using LLM.

        Parameters
        ----------
        user_input : dict | str
            User input to send to LLM.
        response_model : Type[T]
            Pydantic model for response validation.
        system_prompt : str, optional
            Custom system prompt. Uses self.system_prompt if not provided.
        max_output_tokens : int, optional
            Override max output tokens for this call.

        Returns
        -------
        T
            Validated response model instance.
        """
        prompt = system_prompt if system_prompt is not None else self.system_prompt

        user_str = user_input
        if isinstance(user_input, dict):
            user_str = json.dumps(user_input, indent=2, ensure_ascii=False)

        tokens = max_output_tokens or self._max_output_tokens
        raw_response = self.llm.complete(
            system=prompt,
            user=user_str,
            response_schema=response_model.model_json_schema(),
            max_output_tokens=tokens,
        )

        json_text = extract_json(raw_response)
        try:
            data_dict = safe_json_load(json_text)
        except Exception:
            logger.error(
                "JSON parse failed | response length=%d | tail=%s",
                len(raw_response),
                raw_response[-200:],
            )
            raise

        time.sleep(3)  # Prevent API rate limit
        return response_model.model_validate(data_dict)
