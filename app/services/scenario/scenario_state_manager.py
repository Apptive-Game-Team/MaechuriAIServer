# app/services/scenario/scenario_state_manager.py
import logging
import os
import json
from pathlib import Path
from typing import Any, Optional, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ScenarioStateManager:
    def __init__(self, base_tmp_dir: Path = None):
        if base_tmp_dir:
            self.base_tmp_dir = base_tmp_dir
        else:
            self.base_tmp_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.scenario_tmp_dir = self.base_tmp_dir / "scenario_generation"
        os.makedirs(self.scenario_tmp_dir, exist_ok=True)
        logger.info(f"ScenarioStateManager initialized. Temporary directory: {self.scenario_tmp_dir}")

    def _get_temp_filepath(self, request_id: str, step_name: str) -> Path:
        """Constructs a standardized path for intermediate JSON files."""
        return self.scenario_tmp_dir / f"{request_id}_{step_name}.json"

    def save_intermediate_state(self, request_id: str, step_name: str, data: Any):
        """Saves intermediate generation state to a JSON file or raw text file."""
        filepath = self._get_temp_filepath(request_id, step_name)
        try:
            if isinstance(data, BaseModel):
                content = data.model_dump_json(indent=2)
            elif isinstance(data, str):
                content = data
            else:
                content = json.dumps(data, indent=2, ensure_ascii=False)
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"Intermediate state for '{step_name}' saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save intermediate state for '{step_name}' to {filepath}: {e}")

    def load_intermediate_state(self, request_id: str, step_name: str, model_type: Optional[Type[BaseModel]] = None) -> Any:
        """Loads intermediate generation state from a file and optionally parses it into a Pydantic model."""
        filepath = self._get_temp_filepath(request_id, step_name)
        if not filepath.exists():
            return None
        try:
            content = filepath.read_text(encoding='utf-8')
            if model_type:
                instance = model_type.model_validate_json(content)
                logger.info(f"Intermediate state for '{step_name}' loaded from {filepath}")
                return instance
            else:
                # For raw string content, like case_state
                logger.info(f"Intermediate string state for '{step_name}' loaded from {filepath}")
                return content
        except Exception as e:
            logger.error(f"Failed to load or parse intermediate state for '{step_name}' from {filepath}: {e}")
            # Optionally, clean up corrupted file
            # filepath.unlink(missing_ok=True)
            return None
