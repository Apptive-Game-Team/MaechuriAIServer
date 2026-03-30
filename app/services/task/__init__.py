__all__ = ["ScenarioTaskStore"]


def __getattr__(name: str):
    if name == "ScenarioTaskStore":
        from app.features.global_.task.scenario_task_store import ScenarioTaskStore
        return ScenarioTaskStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
