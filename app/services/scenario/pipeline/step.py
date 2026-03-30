"""Abstract base class for a declarative scenario generation pipeline step."""
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional, Type

from pydantic import BaseModel


class PipelineStep(ABC):
    """Abstract base for a single step in the scenario generation pipeline.

    Each step declares its data dependencies and output, allowing the
    :class:`PipelineRunner` to automatically:

    1. Build a dependency graph from ``input_keys`` / ``output_key``.
    2. Execute steps in topological order.
    3. Cache intermediate results to disk and resume on restart.

    Class variables
    ---------------
    input_keys : list[str]
        Names of state keys this step reads from the pipeline state dict.
        Keys must either be present in ``initial_state`` or produced by a
        previous step's ``output_key``.
    output_key : str
        Name under which this step's result is stored in the pipeline state.
    schema_type : Type[BaseModel] | None
        Optional Pydantic model used to deserialise a cached JSON result.
        ``None`` means the cached value is returned as a raw string.
    use_json_retry : bool
        Whether the runner should wrap ``run()`` in :class:`JSONParseRetry`.
        Set to ``False`` for steps whose ``run()`` already handles retries
        internally or returns a plain string (not JSON).
    """

    input_keys: ClassVar[list[str]]
    output_key: ClassVar[str]
    schema_type: ClassVar[Optional[Type[BaseModel]]] = None
    use_json_retry: ClassVar[bool] = True

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute this step.

        Parameters are passed as keyword arguments matching ``input_keys``.

        Returns
        -------
        Any
            The step result, stored in the pipeline state under ``output_key``.
        """
