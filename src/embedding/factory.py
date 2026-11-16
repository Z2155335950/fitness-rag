from __future__ import annotations

from src.config import DEFAULT_MODEL
from src.embedding.base import EmbeddingProvider
from src.embedding.sentence_transformer import SentenceTransformerEmbedding


def create_embedding_provider(
    model_name: str = DEFAULT_MODEL,
    *,
    local_files_only: bool = False,
) -> EmbeddingProvider:
    return SentenceTransformerEmbedding(
        model_name,
        local_files_only=local_files_only,
    )
