from __future__ import annotations


def rrf(
    result_lists: list[list[str]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[str]:
    """Reciprocal Rank Fusion：融合多路排名结果，返回融合后的 ID 顺序。"""
    if weights is None:
        weights = [1.0] * len(result_lists)
    scores: dict[str, float] = {}
    for results, weight in zip(result_lists, weights):
        for rank, doc_id in enumerate(results):
            scores[doc_id] = (
                scores.get(doc_id, 0.0)
                + weight / (k + rank + 1)
            )
    return sorted(scores, key=scores.get, reverse=True)


def dedup(ids: list[str]) -> list[str]:
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out
