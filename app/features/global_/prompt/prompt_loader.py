from pathlib import Path


class PromptLoader:
    @staticmethod
    def load(relative_path: str) -> str:
        # app/ 폴더의 절대 경로 계산 (services/prompt/ -> app/)
        app_root = Path(__file__).resolve().parents[2]

        # 'app/' 접두사가 있으면 제거하고 경로 결합
        clean_path = relative_path.replace("app/", "").replace("app\\", "")
        full_path = app_root / clean_path

        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"Failed to load prompt from '{full_path}': {e}")