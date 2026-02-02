import os


class PromptLoader:
    @staticmethod
    def load(relative_path: str) -> str:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if relative_path.startswith("app/"):
            clean_path = relative_path[4:]
        else:
            clean_path = relative_path

        full_path = os.path.join(base_path, clean_path)
        try:
            with open(full_path, "r", encoding="utf-8") as file:
                return file.read()
        except OSError as e:
            raise RuntimeError(f"Failed to load prompt from '{full_path}': {e}") from e