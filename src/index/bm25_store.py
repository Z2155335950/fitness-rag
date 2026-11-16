from __future__ import annotations

import pickle
from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi


class BM25Index:
    def __init__(self, documents: list[dict], bm25: BM25Okapi):
        self.documents = documents
        self.bm25 = bm25
        self.id_to_doc = {doc["id"]: doc for doc in documents}

    @classmethod
    def build(cls, documents: list[dict]) -> "BM25Index":
        tokens = [
            list(jieba.cut(doc["text"]))
            for doc in documents
        ]
        return cls(documents, BM25Okapi(tokens))

    @classmethod
    def load(cls, path: str | Path) -> "BM25Index":
        with Path(path).open("rb") as handle:
            data = pickle.load(handle)
        return cls(data["docs"], data["bm25"])

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            pickle.dump(
                {"bm25": self.bm25, "docs": self.documents},
                handle,
            )

    def search(self, query: str, k: int = 10) -> list[str]:
        tokens = list(jieba.cut(query))
        indexes = self.bm25.get_top_n(
            tokens, list(range(len(self.documents))), n=k
        )
        return [self.documents[index]["id"] for index in indexes]

    @property
    def legacy_data(self) -> dict:
        return {"bm25": self.bm25, "docs": self.documents}
