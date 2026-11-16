from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def embed_documents(
        self, texts: list[str], show_progress_bar: bool = False
    ) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError
