from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, max_output_tokens: int | None = None) -> str:
        pass

    @abstractmethod
    async def acomplete(self, system: str, user: str, max_output_tokens: int | None = None) -> str:
        pass