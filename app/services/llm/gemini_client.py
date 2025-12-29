from google import genai
from google.genai import types
import os

class GeminiClient:
    def __init__(self):
        api_key = os.environ["GEMINI_API_KEY"]
        self.client = genai.Client(api_key=api_key)
        self.model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    def complete(self, system: str, user: str) -> str:
        prompt = (
            "=== SYSTEM ===\n"
            f"{system}\n\n"
            "=== USER ===\n"
            f"{user}"
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        return response.text.strip()
