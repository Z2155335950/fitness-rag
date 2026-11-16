from __future__ import annotations

from sentence_transformers import SentenceTransformer

from src.embedding.base import EmbeddingProvider


class SentenceTransformerEmbedding(EmbeddingProvider):
    def __init__(
        self,
        model_name: str,
        *,
        local_files_only: bool = False,
        query_prefix: str = "为这个句子生成表示以用于检索：",
    ):
        self._model_name = model_name
        self._query_prefix = query_prefix
        self.model = SentenceTransformer(
            model_name, local_files_only=local_files_only
        )

    @property
    def name(self) -> str:
        return self._model_name

    def embed_documents(
        self, texts: list[str], show_progress_bar: bool = False
    ) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=show_progress_bar,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode(
            [self._query_prefix + text],
            normalize_embeddings=True,
        )
        return embedding[0].tolist()
