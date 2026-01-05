import json
from typing import Dict, Any, List

def extract_json(text: str) -> str:
    """
    Extracts the first JSON object found between '{' and '}'.
    """
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            f"LLM output is incomplete JSON:\n{text}"
        )

    return text[start:end + 1]

def safe_json_load(text: str) -> Dict[str, Any]:
    """
    Loads JSON string, repairing common LLM case-sensitivity issues for Booleans and None.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = (
            text.replace("True", "true")
            .replace("False", "false")
            .replace("None", "null")
        )
        return json.loads(repaired)

def format_history(history: List[Dict[str, str]]) -> str:
    """
    Converts a list of chat history dictionaries to a formatted string.
    Expected format of history items: {'role': '...', 'content': '...'}
    """
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])