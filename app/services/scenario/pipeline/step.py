"""Abstract base class for a declarative scenario generation pipeline step."""
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional, Type, TypeAlias, Union

from pydantic import BaseModel


PipelineKey: TypeAlias = Union[str, Type[Any]]


class PipelineStep(ABC):
    """Abstract base for a single step in the scenario generation pipeline.

    Each step declares its data dependencies and output, allowing the
    :class:`PipelineRunner` to automatically:

    1. Build a dependency graph from ``input_keys`` / ``output_key``.
    2. Execute steps in topological order.
    3. Cache intermediate results to disk and resume on restart.

    Class variables
    ---------------
    input_keys : list[PipelineKey]
        Names of state keys this step reads from the pipeline state dict.
        Keys must either be present in ``initial_state`` or produced by a
        previous step's ``output_key``.
    output_key : PipelineKey
        Name under which this step's result is stored in the pipeline state.
    input_aliases : dict[PipelineKey, str]
        Optional mapping for non-string keys to the argument names expected
        by :meth:`run`. If a key is not a string and no alias is provided,
        :class:`ValueError` is raised unless the step overrides
        :meth:`run_with_inputs`.
    schema_type : Type[BaseModel] | None
        Optional Pydantic model used to deserialise a cached JSON result.
        ``None`` means the cached value is returned as a raw string.
    use_json_retry : bool
        Whether the runner should wrap ``run()`` in :class:`JSONParseRetry`.
        Set to ``False`` for steps whose ``run()`` already handles retries
        internally or returns a plain string (not JSON).
    """

    input_keys: ClassVar[list[PipelineKey]]
    output_key: ClassVar[PipelineKey]
    input_aliases: ClassVar[dict[PipelineKey, str]] = {}
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

    def run_with_inputs(self, inputs: dict[PipelineKey, Any]) -> Any:
        """Execute the step with a raw input mapping.

        This default implementation converts ``inputs`` into keyword
        arguments for :meth:`run`.  String keys are passed through
        unchanged.  Non-string keys must be listed in ``input_aliases``
        or this method raises ``ValueError``.  Steps that want full
        control over typed keys can override this method directly.
        """
        kwargs: dict[str, Any] = {}
        for key, value in inputs.items():
            if isinstance(key, str):
                arg_name = key
            else:
                arg_name = self.input_aliases.get(key)
                if arg_name is None:
                    raise ValueError(
                        "Non-string PipelineKey requires input_aliases or "
                        "an overridden run_with_inputs(): "
                        f"{key!r} in {self.__class__.__name__}"
                    )
            kwargs[arg_name] = value
        return self.run(**kwargs)
