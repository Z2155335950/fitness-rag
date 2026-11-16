from __future__ import annotations

from pathlib import Path

import chromadb

from src.vectorstore.base import VectorStore


class ChromaVectorStore(VectorStore):
    def __init__(
        self,
        path: str | Path,
        collection_name: str = "fitness",
    ):
        self.path = str(path)
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=self.path)
        self.collection = self.client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self.collection.count()

    def add(self, *, ids, documents, embeddings, metadatas) -> None:
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(self, embedding: list[float], k: int) -> list[str]:
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(k, max(self.count(), 1)),
        )
        return result["ids"][0] if result["ids"] else []

    def get_existing(self, ids: list[str]) -> list[str]:
        if not ids:
            return []
        result = self.collection.get(ids=list(dict.fromkeys(ids)))
        return result["ids"]

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
