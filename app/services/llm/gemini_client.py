from google import genai
from google.genai import types
from google.genai.errors import ClientError
import time
from .llm_client import LLMClient
import os

class GeminiClient(LLMClient):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please configure your Gemini API key before using GeminiClient."
            )
        self.client = genai.Client(api_key=api_key)
        self.model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    def complete(self,
                 system: str,
                 user: str = "",
                 response_schema: dict | None = None) -> str:
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
            config_params["response_schema"] = response_schema
        else:
            # Default behavior if needed, or just plain text
            pass

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
                # 429 에러(Quota Exceeded)인 경우 지수적 대기 후 재시도
                if e.code == 429 or 'RESOURCE_EXHAUSTED' in str(e):
                    if attempt < max_retries:
                        sleep_time = base_delay * (2 ** attempt)
                        print(f"Gemini API Quota exceeded. Retrying in {sleep_time}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(sleep_time)
                        continue
                # 다른 에러이거나 재시도 횟수를 초과한 경우 에러 발생
                raise e

        return "Error"