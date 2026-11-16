from __future__ import annotations

import math

from src.vectorstore.base import VectorStore


class InMemoryVectorStore(VectorStore):
    """Small deterministic store used by tests and adapters."""

    def __init__(self):
        self.ids: list[str] = []
        self.documents: list[str] = []
        self.embeddings: list[list[float]] = []
        self.metadatas: list[dict] = []

    def count(self) -> int:
        return len(self.ids)

    def add(self, *, ids, documents, embeddings, metadatas) -> None:
        self.ids.extend(ids)
        self.documents.extend(documents)
        self.embeddings.extend(embeddings)
        self.metadatas.extend(metadatas)

    def search(self, embedding: list[float], k: int) -> list[str]:
        def similarity(other: list[float]) -> float:
            numerator = sum(a * b for a, b in zip(embedding, other))
            left = math.sqrt(sum(a * a for a in embedding))
            right = math.sqrt(sum(b * b for b in other))
            return numerator / (left * right) if left and right else 0.0

        ranked = sorted(
            zip(self.ids, self.embeddings),
            key=lambda item: similarity(item[1]),
            reverse=True,
        )
        return [doc_id for doc_id, _ in ranked[:k]]

    def get_existing(self, ids: list[str]) -> list[str]:
        existing = set(self.ids)
        return [doc_id for doc_id in ids if doc_id in existing]

    def reset(self) -> None:
        self.ids.clear()
        self.documents.clear()
        self.embeddings.clear()
        self.metadatas.clear()
