from __future__ import annotations

from pathlib import Path

from src.config import COLLECTION_NAME
from src.vectorstore.base import VectorStore
from src.vectorstore.chroma_store import ChromaVectorStore


def create_vector_store(
    path: str | Path,
    collection_name: str = COLLECTION_NAME,
) -> VectorStore:
    return ChromaVectorStore(path, collection_name)
