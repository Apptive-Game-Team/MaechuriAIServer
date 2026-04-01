"""Pipeline runner with topological-sort auto-scheduling and disk caching."""
import logging
from typing import Any, Optional

from app.core.json_retry import JSONParseRetry
from app.services.scenario.pipeline.step import PipelineStep, PipelineKey
from app.services.scenario.scenario_state_manager import ScenarioStateManager

logger = logging.getLogger(__name__)

# Default JSONParseRetry policy shared by PipelineRunner and ScenarioService.
# Keep these in one place so that changes apply consistently everywhere.
DEFAULT_JSON_RETRY_MAX_ATTEMPTS = 3
DEFAULT_JSON_RETRY_BACKOFF_SECONDS = 2.0
DEFAULT_JSON_RETRY_BACKOFF_MULTIPLIER = 1.5


def _default_json_retry() -> JSONParseRetry:
    """Return a JSONParseRetry instance with the project-wide default policy."""
    return JSONParseRetry(
        max_attempts=DEFAULT_JSON_RETRY_MAX_ATTEMPTS,
        backoff_seconds=DEFAULT_JSON_RETRY_BACKOFF_SECONDS,
        backoff_multiplier=DEFAULT_JSON_RETRY_BACKOFF_MULTIPLIER,
    )


def _key_to_cache_name(key: PipelineKey) -> str:
    """Convert a PipelineKey into a stable cache/file name."""
    if isinstance(key, str):
        return key
    if isinstance(key, type):
        return f"{key.__module__}.{key.__qualname__}"
    return str(key)


class PipelineRunner:
    """Executes :class:`PipelineStep` instances in dependency order.

    Features
    --------
    Auto-scheduling
        The execution order is derived from each step's declared
        ``input_keys`` and ``output_key`` via a topological sort (Kahn's
        algorithm).  Keys may be either strings or Python types.  Circular
        dependencies raise :class:`ValueError` at construction time.
    Caching
        Before running a step, the runner checks
        :class:`ScenarioStateManager` for a persisted result.  If found,
        the cached value is used and the LLM is not called.  This enables
        crash-recovery and iterative development.
    JSON retry
        Steps with ``use_json_retry = True`` are wrapped in
        :class:`JSONParseRetry` to handle transient LLM parse errors.

    Parameters
    ----------
    steps : list[PipelineStep]
        Unordered list of steps.  Order is determined automatically.
    state_manager : ScenarioStateManager
        Handles disk-based intermediate state persistence.
    json_retry : JSONParseRetry, optional
        Retry policy for JSON parsing failures.  A default policy is used
        when not provided.
    """

    def __init__(
        self,
        steps: list[PipelineStep],
        state_manager: ScenarioStateManager,
        json_retry: Optional[JSONParseRetry] = None,
    ) -> None:
        self._state_manager = state_manager
        self._json_retry = json_retry or _default_json_retry()
        self._ordered_steps = self._topological_sort(steps)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        initial_state: dict[PipelineKey, Any],
        request_id: str,
    ) -> dict[PipelineKey, Any]:
        """Execute all steps in dependency order.

        Steps whose output is already cached are skipped; all others are
        executed and their results persisted to disk.

        Parameters
        ----------
        initial_state : dict[PipelineKey, Any]
        Seed data for the pipeline (e.g. ``{"theme": "random"}``).
        All keys required by the first steps must be present here.
        request_id : str
            Unique identifier for this pipeline run, used as a cache key.

        Returns
        -------
        dict[PipelineKey, Any]
            Final pipeline state containing every step's output plus the
            original ``initial_state`` entries.

        Raises
        ------
        RuntimeError
            If a step fails after all retry attempts.
        """
        state = dict(initial_state)

        for step in self._ordered_steps:
            output_key = step.output_key
            cache_key = _key_to_cache_name(output_key)

            cached = self._state_manager.load_intermediate_state(
                request_id, cache_key, step.schema_type
            )
            if cached is not None:
                logger.info("[Pipeline] Loaded '%s' from cache.", cache_key)
                state[output_key] = cached
                continue

            logger.info(
                "[Pipeline] Running %s → '%s'",
                step.__class__.__name__,
                cache_key,
            )
            inputs = {k: state[k] for k in step.input_keys}

            if step.use_json_retry:
                # Pass the step as `generator` only when it exposes
                # _max_output_tokens (used by JSONParseRetry for token
                # escalation on successive attempts).
                generator = step if hasattr(step, "_max_output_tokens") else None
                result = self._json_retry.parse_with_retry(
                    parser_func=lambda s=step, i=inputs: s.run_with_inputs(i),
                    schema_name=cache_key,
                    generator=generator,
                )
                if result is None:
                    raise RuntimeError(
                        f"Pipeline step '{cache_key}' failed after all retries."
                    )
            else:
                result = step.run_with_inputs(inputs)

            self._state_manager.save_intermediate_state(
                request_id, cache_key, result
            )
            state[output_key] = result

        return state

    def clear(self, request_id: str, *output_keys: PipelineKey) -> None:
        """Remove cached results for the specified step outputs.

        Call this before re-running the pipeline when earlier steps need
        to be regenerated (e.g. after a critic or clearability failure).

        Parameters
        ----------
        request_id : str
            The pipeline run whose cached data should be cleared.
        *output_keys : str
            One or more ``output_key`` values to invalidate.
        """
        for key in output_keys:
            cache_key = _key_to_cache_name(key)
            self._state_manager.clear_intermediate_state(request_id, cache_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _topological_sort(
        self, steps: list[PipelineStep]
    ) -> list[PipelineStep]:
        """Return *steps* sorted so every step's inputs are satisfied.

        Uses Kahn's algorithm on the dependency graph implied by each
        step's ``input_keys`` and ``output_key``.

        Raises
        ------
        ValueError
            If the steps contain a circular dependency.
        """
        output_to_step: dict[PipelineKey, PipelineStep] = {
            step.output_key: step for step in steps
        }

        in_degree: dict[PipelineKey, int] = {
            step.output_key: 0 for step in steps
        }
        dependents: dict[PipelineKey, list[PipelineKey]] = {
            step.output_key: [] for step in steps
        }

        for step in steps:
            for input_key in step.input_keys:
                if input_key in output_to_step:
                    in_degree[step.output_key] += 1
                    dependents[input_key].append(step.output_key)

        queue: list[PipelineKey] = [
            key for key, degree in in_degree.items() if degree == 0
        ]
        sorted_keys: list[PipelineKey] = []

        while queue:
            key = queue.pop(0)
            sorted_keys.append(key)
            for dependent_key in dependents[key]:
                in_degree[dependent_key] -= 1
                if in_degree[dependent_key] == 0:
                    queue.append(dependent_key)

        if len(sorted_keys) != len(steps):
            raise ValueError(
                "Circular dependency detected among pipeline steps: "
                + repr([s.__class__.__name__ for s in steps])
            )

        return [output_to_step[key] for key in sorted_keys]
