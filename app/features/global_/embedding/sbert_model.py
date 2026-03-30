from typing import List
from sentence_transformers import SentenceTransformer
from app.features.global_.embedding.embedding_model import EmbeddingModel


DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

class SBERTModel(EmbeddingModel):
    """Embedding model based on Sentence-BERT (SBERT).

    This class wraps a `sentence_transformers.SentenceTransformer` model
    and exposes a simple interface for turning input text into dense
    vector embeddings.
    """

    def __init__(self, model_name_or_path: str = DEFAULT_MODEL) -> None:
        """Initialize the SBERTModel.

        Parameters
        ----------
        model_name_or_path : str, optional
            The name of, or local path to, a SentenceTransformer model to load.
            Defaults to ``DEFAULT_MODEL``.
        """
        self.model = SentenceTransformer(model_name_or_path)

    def embed(self, text: str) -> List[float]:
        """Compute an embedding vector for the given text.

        Parameters
        ----------
        text : str
            The input text to encode as an embedding.

        Returns
        -------
        List[float]
            The embedding of the input text as a list of floating-point values.
        """
        return self.model.encode(text).tolist()


if __name__ == "__main__":
    from sentence_transformers import util
    import torch

    print("loading model...")
    model = SBERTModel()
    print("successfully loaded!")

    sentence1 = "안녕하세요 저는 이요환입니다."
    sentence2 = "hello, i am Lee."
    sentence3 = "i am hungry"

    print("calculating embeddings...")
    embedding1 = torch.tensor(model.embed(sentence1))
    embedding2 = torch.tensor(model.embed(sentence2))
    embedding3 = torch.tensor(model.embed(sentence3))
    print("successfully calculated!")

    print("calculating similarity...")
    print(f"similarity '{sentence1}' and '{sentence2}': {util.cos_sim(embedding1, embedding2).tolist()}")
    print(f"similarity '{sentence2}' and '{sentence3}': {util.cos_sim(embedding2, embedding3).tolist()}")
    print("successfully calculated!")
