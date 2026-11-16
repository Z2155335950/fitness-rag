from __future__ import annotations

from abc import ABC, abstractmethod


class VectorStore(ABC):
    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def add(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, embedding: list[float], k: int) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_existing(self, ids: list[str]) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError
