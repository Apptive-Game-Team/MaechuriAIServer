"""Embedding service for generating and managing embeddings."""
from typing import List, Optional

from app.db.models import Fact
from app.features.global_.embedding.bge_m3_model import get_embedding_model, BGEM3Model


class EmbeddingService:
    """Service for generating embeddings from various data types.

    Handles text composition and embedding generation for different entity types
    used in RAG retrieval.
    """

    def __init__(self, model: Optional[BGEM3Model] = None):
        """Initialize the embedding service.

        Parameters
        ----------
        model : BGEM3Model, optional
            The embedding model to use. Uses singleton if not provided.
        """
        self.model = model or get_embedding_model()

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Parameters
        ----------
        text : str
            The text to embed.

        Returns
        -------
        List[float]
            The embedding vector.
        """
        return self.model.embed(text)

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query.

        Parameters
        ----------
        query : str
            The query text.

        Returns
        -------
        List[float]
            The query embedding.
        """
        return self.model.embed_query(query)

    def embed_suspect_profile(
        self,
        name: str,
        role: str,
        description: str,
        age: int,
        gender: str
    ) -> List[float]:
        """Generate embedding for suspect profile.

        Parameters
        ----------
        name : str
            Suspect name.
        role : str
            Suspect role/occupation.
        description : str
            Physical description.
        age : int
            Suspect age.
        gender : str
            Suspect gender.

        Returns
        -------
        List[float]
            The profile embedding.
        """
        text = f"이름: {name}, 직업/역할: {role}, 나이: {age}세, 성별: {gender}. 외모: {description}"
        return self.model.embed(text)

    def embed_fact(
        self,
        fact: Fact
    ) -> List[float]:
        """Generate embedding for a fact."""
        text = None
        match fact.type:
            case "secret":
                text = self._serialize_secret(
                    fact.content,
                    fact.suspect.name)
            case "timeline":
                text = self._serialize_timeline(
                    fact.content["time"],
                    fact.content["location"],
                    fact.content["activity"],
                    fact.suspect.name)
            case _:
                text = fact.to_string()

        return self.model.embed(text)

    def _serialize_timeline(
        self,
        time: str,
        location: str,
        activity: str,
        suspect_name: str = ""
    ) -> str:
        if suspect_name:
            return f"{suspect_name}의 행적: {time}에 {location}에서 {activity}"
        else:
            return f"시간: {time}, 장소: {location}, 행동: {activity}"

    def _serialize_secret(self, content: str, suspect_name: str = "") -> str:
        if suspect_name:
            return f"{suspect_name}의 비밀: {content}"
        else:
            return f"비밀: {content}"

    def embed_clue_description(
        self,
        name: str,
        description: str,
        found_at: str
    ) -> List[float]:
        """Generate embedding for clue description.

        Parameters
        ----------
        name : str
            Clue name.
        description : str
            Clue description.
        found_at : str
            Location where clue was found.

        Returns
        -------
        List[float]
            The description embedding.
        """
        text = f"증거: {name}. 발견 장소: {found_at}. 설명: {description}"
        return self.model.embed(text)

    def embed_clue_logic(
        self,
        name: str,
        logic_explanation: str,
        decoded_answer: Optional[str] = None
    ) -> List[float]:
        """Generate embedding for clue logic/analysis.

        Parameters
        ----------
        name : str
            Clue name.
        logic_explanation : str
            Logical explanation of the clue.
        decoded_answer : str, optional
            Decoded meaning of the clue.

        Returns
        -------
        List[float]
            The logic embedding.
        """
        text = f"증거 '{name}'의 분석: {logic_explanation}"
        if decoded_answer:
            text += f" 해석: {decoded_answer}"
        return self.model.embed(text)

    def embed_chat_message(
        self,
        role: str,
        content: str,
        context: str = ""
    ) -> List[float]:
        """Generate embedding for a chat message.

        Parameters
        ----------
        role : str
            Message role (user, suspect, detective).
        content : str
            Message content.
        context : str, optional
            Additional context (e.g., suspect name).

        Returns
        -------
        List[float]
            The message embedding.
        """
        role_map = {
            "user": "탐정",
            "detective": "탐정",
            "suspect": "용의자"
        }
        role_label = role_map.get(role, role)

        if context:
            text = f"[{context}] {role_label}: {content}"
        else:
            text = f"{role_label}: {content}"
        return self.model.embed(text)

    def embed_batch_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Parameters
        ----------
        texts : List[str]
            The texts to embed.
        batch_size : int, optional
            Batch size for processing. Defaults to 32.

        Returns
        -------
        List[List[float]]
            List of embedding vectors.
        """
        return self.model.embed_batch(texts, batch_size=batch_size)


# Singleton instance
_service_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the singleton embedding service instance.

    Returns
    -------
    EmbeddingService
        The embedding service instance.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = EmbeddingService()
    return _service_instance
