from abc import ABC
from typing import List


class EmbeddingModel(ABC):

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError