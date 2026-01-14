from abc import ABC, abstractmethod
from typing import List


class EmbeddingModel(ABC):
class EmbeddingModel(ABC):
    """
    Abstract base class for text embedding models.

    Subclasses are expected to provide a concrete implementation of
    :meth:`embed` that converts input text into a fixed-size numeric vector
    representation suitable for downstream tasks (e.g., similarity search,
    retrieval, or classification).
    """

    def embed(self, text: str) -> List[float]:
        """
        Compute an embedding vector for the given input text.

        Parameters
        ----------
        text : str
            The input text to be encoded into a numeric embedding.

        Returns
        -------
        List[float]
            A list of floating-point values representing the embedding vector
            for the input text. The dimensionality and semantics of the
            vector are defined by the concrete implementation.

        Raises
        ------
        NotImplementedError
            If the method is not implemented by a subclass.
        """
        raise NotImplementedError