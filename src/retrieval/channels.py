from __future__ import annotations

from src.embedding.base import EmbeddingProvider
from src.index.bm25_store import BM25Index
from src.query.schema import EntityType, Intent, RoutedQuery
from src.vectorstore.base import VectorStore


def exact_action(rq: RoutedQuery, store: VectorStore) -> list[str]:
    """意图=动作详情：直接从实体拿 ID，不走向量。"""
    ids: list[str] = []
    for e in rq.entities:
        if e.type in (EntityType.ACTION, EntityType.ACTION_GROUP):
            ids.extend(e.ids)
    if not ids:
        return []
    # 保持实体出现顺序
    existing = set(store.get_existing(list(dict.fromkeys(ids))))
    return [i for i in ids if i in existing]


def muscle_reverse(rq: RoutedQuery, reverse_index: dict) -> list[str]:
    """意图=练某肌肉：查反向索引拿动作 ID。"""
    ids: list[str] = []
    for e in rq.entities:
        if e.type in (EntityType.MUSCLE, EntityType.MUSCLE_GROUP):
            for mid in e.ids:
                ids.extend(reverse_index.get(mid, []))
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def vector(
    query: str,
    embeddings: EmbeddingProvider,
    store: VectorStore,
    k: int = 10,
) -> list[str]:
    """Embedding provider and vector store are independently replaceable."""
    return store.search(embeddings.embed_query(query), k)


def bm25_recall(
    query: str, bm25: BM25Index, k: int = 10
) -> list[str]:
    """BM25 召回（jieba 分词）。"""
    return bm25.search(query, k)
