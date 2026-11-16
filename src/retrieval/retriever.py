from __future__ import annotations

import json
from pathlib import Path

from src.config import (
    COLLECTION_NAME,
    DB_DIR,
    DEFAULT_MODEL,
    FIELD_COLLECTION_NAME,
    PARSED_DIR,
)
from src.embedding.base import EmbeddingProvider
from src.embedding.factory import create_embedding_provider
from src.index.bm25_store import BM25Index
from src.query.schema import EntityType, Intent, RoutedQuery
from src.vectorstore.base import VectorStore
from src.vectorstore.factory import create_vector_store

from .channels import bm25_recall, exact_action, muscle_reverse, vector
from .fusion import dedup, rrf


class Retriever:
    """Orchestrates retrieval through replaceable infrastructure interfaces."""

    def __init__(
        self,
        parsed_dir: str | Path = PARSED_DIR,
        db_dir: str | Path = DB_DIR,
        model_name: str = DEFAULT_MODEL,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
        bm25_index: BM25Index | None = None,
        field_vector_store: VectorStore | None = None,
        field_bm25_index: BM25Index | None = None,
    ):
        self.parsed_dir = Path(parsed_dir)
        self.db_dir = Path(db_dir)

        bm_path = self.db_dir / "bm25.pkl"
        if bm25_index is None and not bm_path.exists():
            raise FileNotFoundError(
                f"缺少 {bm_path}，请先运行：python -m src.index.build_index"
            )
        self.bm25 = bm25_index or BM25Index.load(bm_path)
        field_bm_path = self.db_dir / "bm25_fields.pkl"
        self.field_bm25 = field_bm25_index or (
            BM25Index.load(field_bm_path)
            if field_bm_path.exists()
            else None
        )

        reverse_path = self.parsed_dir / "reverse_index.json"
        self.reverse_index = (
            json.loads(reverse_path.read_text(encoding="utf-8"))
            if reverse_path.exists()
            else {}
        )

        self.embeddings = embedding_provider or create_embedding_provider(
            model_name,
            local_files_only=True,
        )
        self.vector_store = vector_store or create_vector_store(
            self.db_dir / "chroma",
            COLLECTION_NAME,
        )
        self.field_vector_store = field_vector_store or create_vector_store(
            self.db_dir / "chroma_fields",
            FIELD_COLLECTION_NAME,
        )
        self.id_to_doc = self.bm25.id_to_doc
        self.field_id_to_doc = (
            self.field_bm25.id_to_doc if self.field_bm25 else {}
        )

    def _filter_by_meta_map(
        self,
        ids: list[str],
        doc_map: dict[str, dict],
        filters: dict,
        *,
        relax: bool = False,
    ) -> list[str]:
        if not filters:
            return ids
        kept: list[str] = []
        for doc_id in ids:
            meta = doc_map.get(doc_id, {}).get("meta", {})
            if (
                "difficulty" in filters
                and meta.get("difficulty") not in filters["difficulty"]
            ):
                continue
            equipment = meta.get("equipment")
            if (
                "equipment_include" in filters
                and equipment not in filters["equipment_include"]
            ):
                continue
            if (
                "equipment_exclude" in filters
                and equipment in filters["equipment_exclude"]
            ):
                continue
            if "body_parts" in filters:
                part = meta.get("part") or meta.get("group") or ""
                prefixes = [
                    bp[:2].removesuffix("肌") for bp in filters["body_parts"]
                ]
                if not any(prefix and prefix in part for prefix in prefixes):
                    continue
            kept.append(doc_id)
        if relax and ids and not kept:
            return ids
        return kept

    def _filter_by_meta(
        self, ids: list[str], filters: dict, *, relax: bool = False
    ) -> list[str]:
        return self._filter_by_meta_map(
            ids,
            self.id_to_doc,
            filters,
            relax=relax,
        )

    def _field_parent_candidates(
        self,
        rq: RoutedQuery,
        k: int,
        trace: dict | None = None,
    ) -> list[str]:
        fields = set(rq.filters.get("fields", []))
        if not fields or self.field_bm25 is None:
            return []
        labels = {
            "errors": "常见错误",
            "cues": "动作要点",
            "tips": "训练提示",
            "targets": "目标肌群",
        }
        query = rq.raw + " " + " ".join(
            labels[field] for field in fields if field in labels
        )
        field_vector_ids = vector(
            query,
            self.embeddings,
            self.field_vector_store,
            k=k,
        )
        field_bm25_ids = bm25_recall(query, self.field_bm25, k=k)
        field_ids = rrf([field_vector_ids, field_bm25_ids])
        if trace is not None:
            trace["field_vector_ids"] = field_vector_ids
            trace["field_bm25_ids"] = field_bm25_ids
        field_ids = [
            doc_id
            for doc_id in field_ids
            if self.field_id_to_doc.get(doc_id, {})
            .get("meta", {})
            .get("field")
            in fields
        ]
        field_ids = self._filter_by_meta_map(
            field_ids, self.field_id_to_doc, rq.filters
        )
        parents = []
        for doc_id in field_ids:
            parent_id = self.field_id_to_doc[doc_id]["meta"].get(
                "parent_id"
            )
            if parent_id and parent_id not in parents:
                parents.append(parent_id)
        if trace is not None:
            trace["field_ids"] = field_ids
            trace["field_parent_ids"] = parents
        return parents

    def _prefer_bodyweight(self, ids: list[str], filters: dict) -> list[str]:
        if not filters.get("prefer_bodyweight"):
            return ids
        return sorted(
            ids,
            key=lambda doc_id: (
                self.id_to_doc.get(doc_id, {})
                .get("meta", {})
                .get("equipment")
                != "自重"
            ),
        )

    def retrieve_with_trace(
        self, rq: RoutedQuery, top_k: int = 5
    ) -> tuple[list[dict], dict]:
        intent = rq.intent
        trace = {
            "intent": intent.value,
            "filters": rq.filters,
            "entities": [
                {
                    "text": entity.text,
                    "canonical": entity.canonical,
                    "type": entity.type.value,
                    "ids": entity.ids,
                }
                for entity in rq.entities
            ],
            "exact_ids": [],
            "reverse_ids": [],
            "vector_ids": [],
            "bm25_ids": [],
            "field_vector_ids": [],
            "field_bm25_ids": [],
            "field_ids": [],
        }

        if intent == Intent.ACTION_DETAIL:
            ids = exact_action(rq, self.vector_store)
            trace["exact_ids"] = list(ids)
            ids = self._filter_by_meta(ids, rq.filters)
            if len(ids) < top_k:
                vec_ids = vector(
                    rq.raw,
                    self.embeddings,
                    self.vector_store,
                    k=top_k * 3,
                )
                trace["vector_ids"] = vec_ids
                ids += vec_ids
            ids = dedup(ids)

        elif intent == Intent.MUSCLE_TO_ACTIONS:
            ids = muscle_reverse(rq, self.reverse_index)
            trace["reverse_ids"] = list(ids)
            ids = self._filter_by_meta(ids, rq.filters)
            ids = self._prefer_bodyweight(ids, rq.filters)
            if len(ids) < top_k:
                vec_ids = vector(
                    rq.raw,
                    self.embeddings,
                    self.vector_store,
                    k=top_k * 3,
                )
                trace["vector_ids"] = vec_ids
                vec_ids = self._filter_by_meta(
                    vec_ids, rq.filters, relax=True
                )
                ids = rrf([ids, vec_ids])
            ids = self._prefer_bodyweight(dedup(ids), rq.filters)

        elif intent == Intent.FILTER:
            vec_ids = vector(
                rq.raw,
                self.embeddings,
                self.vector_store,
                k=top_k * 4,
            )
            bm_ids = bm25_recall(rq.raw, self.bm25, k=top_k * 4)
            trace["vector_ids"] = vec_ids
            trace["bm25_ids"] = bm_ids
            ids = rrf([vec_ids, bm_ids])
            ids = self._filter_by_meta(ids, rq.filters)
            ids = dedup(ids)

        else:
            vec_ids = vector(
                rq.raw,
                self.embeddings,
                self.vector_store,
                k=top_k * 4,
            )
            bm_ids = bm25_recall(rq.raw, self.bm25, k=top_k * 4)
            trace["vector_ids"] = vec_ids
            trace["bm25_ids"] = bm_ids
            ids = rrf([vec_ids, bm_ids])

        has_action_entity = any(
            entity.type in {EntityType.ACTION, EntityType.ACTION_GROUP}
            for entity in rq.entities
        )
        if rq.filters.get("fields") and not has_action_entity:
            field_parents = self._field_parent_candidates(
                rq, k=top_k * 5, trace=trace
            )
            if field_parents:
                ids = rrf(
                    [field_parents, dedup(ids)],
                    weights=[2.0, 1.0],
                )

        if intent == Intent.ACTION_DETAIL:
            has_exact_action = any(
                entity.type == EntityType.ACTION
                for entity in rq.entities
            )
            viewpoint_limit = 4 if has_exact_action else 1
            ranked_action_ids = [
                doc_id
                for doc_id in ids
                if self.id_to_doc.get(doc_id, {})
                .get("meta", {})
                .get("kind")
                == "action"
            ]
            if not ranked_action_ids:
                ranked_action_ids = [
                    action_id
                    for entity in rq.entities
                    if entity.type
                    in {EntityType.ACTION, EntityType.ACTION_GROUP}
                    for action_id in entity.ids
                ]
            related_viewpoints = []
            # Attach only opinions belonging to the primary action.
            for action_id in ranked_action_ids[:1]:
                for doc_id, doc in self.id_to_doc.items():
                    meta = doc.get("meta", {})
                    if (
                        meta.get("kind") == "viewpoint"
                        and meta.get("action_id") == action_id
                    ):
                        related_viewpoints.append(doc_id)
                if len(related_viewpoints) >= viewpoint_limit:
                    break
            related_viewpoints = related_viewpoints[:viewpoint_limit]
            if related_viewpoints:
                ids = dedup(ids[:1] + related_viewpoints + ids[1:])

        final_docs = [
            self.id_to_doc[doc_id]
            for doc_id in ids[:top_k]
            if doc_id in self.id_to_doc
        ]
        trace["final_ids"] = [doc["id"] for doc in final_docs]
        return final_docs, trace

    def retrieve(self, rq: RoutedQuery, top_k: int = 5) -> list[dict]:
        docs, _ = self.retrieve_with_trace(rq, top_k)
        return docs
