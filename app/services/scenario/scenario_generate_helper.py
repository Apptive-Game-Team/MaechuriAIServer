from typing import Any, List

from app.models.schemas.suspect import SuspectListSchema
from app.models.schemas.suspect.common import FactEntrySchema


def find_facts(suspect_list: SuspectListSchema) -> List[FactEntrySchema[Any]]:
    suspect_facts: List[FactEntrySchema] = []
    for suspect in suspect_list.suspects:
        suspect_facts.extend(suspect.secrets)
        suspect_facts.extend(suspect.facts)

    return suspect_facts

def inject_sequential_id(obj: Any, id_name: str):
    """Inject sequential id."""
    _inject_sequential_id(obj, id_name, 1)

def _inject_sequential_id(obj: Any, id_name: str, start_id: int) -> int:
    id_counter = start_id

    """Inject sequential id."""
    if isinstance(obj, list):
        for item in obj:
            id_counter = _inject_sequential_id(item, id_name, id_counter)

    if hasattr(obj, "__dict__"):
        for attr_name in list(obj.__dict__.keys()):
            if attr_name == id_name:
                setattr(obj, attr_name, id_counter)
                id_counter += 1

            child = getattr(obj, attr_name)
            id_counter = _inject_sequential_id(child, id_name, id_counter)

    return id_counter

if __name__ == "__main__":
    class TestObject[T]:
        def __init__(self, child: T = None):
            self.a = 2
            self.b = 3
            self.id = 0
            self.child = child

        def __repr__(self):
            return f"TestObject(id={self.id}, a={self.a}, b={self.b}, child={self.child})"

    obj = TestObject(
        child=TestObject(
            child=TestObject(
                child=100  # 마지막 T는 int
            )
        )
    )

    inject_sequential_id(obj, "id")

    print(obj)
