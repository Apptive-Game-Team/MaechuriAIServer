class PromptLoader:
    @staticmethod
    def load(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as file:
                return file.read()
        except OSError as e:
            raise RuntimeError(f"Failed to load prompt from '{path}': {e}") from e