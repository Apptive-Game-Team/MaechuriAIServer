from google import genai
from google.genai import types
from google.genai.errors import ClientError
import time
import os

from .llm_client import LLMClient


class GeminiClient(LLMClient):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please configure your Gemini API key before using GeminiClient."
            )

        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def complete(
        self,
        system: str,
        user: str = "",
        response_schema: dict | None = None,
    ) -> str:
        prompt = (
            "=== SYSTEM ===\n"
            f"{system}\n\n"
            "=== USER ===\n"
            f"{user}"
        )

        config_params = {
            "temperature": 0.2,
            "max_output_tokens": 8192,
        }

        if response_schema:
            config_params["response_mime_type"] = "application/json"
            # Gemini API does not support 'additionalProperties'
            config_params["response_schema"] = self._sanitize_schema(response_schema)

        max_retries = 5
        base_delay = 2

        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_params),
                )
                return response.text.strip()

            except ClientError as e:
                # Quota / Rate limit
                if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < max_retries:
                        sleep_time = base_delay * (2 ** attempt)
                        print(
                            f"Gemini API quota exceeded. "
                            f"Retrying in {sleep_time}s... "
                            f"(Attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(sleep_time)
                        continue
                raise

        return "Error"

    def _sanitize_schema(self, schema: dict) -> dict:
        """Recursively removes 'additionalProperties' from JSON schema."""
        if isinstance(schema, dict):
            return {
                k: self._sanitize_schema(v)
                for k, v in schema.items()
                if k != "additionalProperties"
            }
        elif isinstance(schema, list):
            return [self._sanitize_schema(item) for item in schema]
        else:
            return schema
