import json
import time
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from app.core.utils import extract_json, safe_json_load

T = TypeVar("T", bound=BaseModel)


class BaseGenerator:
    def __init__(self, llm_client, system_prompt: str):
        self.llm = llm_client
        self.system_prompt = system_prompt

    def _generate(
        self,
        user_input: dict | str,
        response_model: Type[T],
        system_prompt: Optional[str] = None
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

        Returns
        -------
        T
            Validated response model instance.
        """
        prompt = system_prompt if system_prompt is not None else self.system_prompt

        user_str = user_input
        if isinstance(user_input, dict):
            user_str = json.dumps(user_input, indent=2, ensure_ascii=False)

        raw_response = self.llm.complete(
            system=prompt,
            user=user_str,
            response_schema=response_model.model_json_schema()
        )

        json_text = extract_json(raw_response)
        data_dict = safe_json_load(json_text)

        time.sleep(3)  # Prevent API rate limit
        return response_model.model_validate(data_dict)
