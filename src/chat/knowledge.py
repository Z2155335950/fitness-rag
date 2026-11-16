from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from pathlib import Path

from src.chat.contracts import (
    ConversationIntent,
    KnowledgeSearchResult,
    KnowledgeSnippet,
    TrainingProfile,
)
from src.chat.query_planner import TrainingQueryPlanner
from src.config import DB_DIR, DEFAULT_MODEL, PARSED_DIR


class KnowledgeProvider(ABC):
    @abstractmethod
    def search(
        self,
        message: str,
        profile: TrainingProfile,
        intent: ConversationIntent,
        top_k: int = 6,
    ) -> KnowledgeSearchResult:
        raise NotImplementedError


class EmptyKnowledgeProvider(KnowledgeProvider):
    def search(
        self,
        message: str,
        profile: TrainingProfile,
        intent: ConversationIntent,
        top_k: int = 6,
    ) -> KnowledgeSearchResult:
        return KnowledgeSearchResult()


class RAGKnowledgeProvider(KnowledgeProvider):
    """Adapts the existing RAG engine into chat-friendly evidence snippets."""

    def __init__(
        self,
        parsed_dir: str | Path = PARSED_DIR,
        db_dir: str | Path = DB_DIR,
        model_name: str = DEFAULT_MODEL,
    ):
        self.parsed_dir = parsed_dir
        self.db_dir = db_dir
        self.model_name = model_name
        self._rag = None
        self._lock = threading.Lock()
        self.query_planner = TrainingQueryPlanner()

    def _get_rag(self):
        if self._rag is None:
            with self._lock:
                if self._rag is None:
                    from src.rag import FitnessRAG

                    self._rag = FitnessRAG(
                        self.parsed_dir, self.db_dir, self.model_name
                    )
        return self._rag

    @staticmethod
    def _profile_query(profile: TrainingProfile) -> str:
        values = [
            profile.goal or "",
            profile.experience or "",
            "、".join(profile.equipment),
        ]
        return " ".join(value for value in values if value)

    def search(
        self,
        message: str,
        profile: TrainingProfile,
        intent: ConversationIntent,
        top_k: int = 6,
    ) -> KnowledgeSearchResult:
        rag = self._get_rag()
        planned_queries = self.query_planner.plan(
            message, profile, intent, top_k
        )

        docs = []
        seen: set[str] = set()
        retrieval_trace = []
        for planned in planned_queries:
            routed = rag.pipeline.process(planned.text)
            retrieved, trace = rag.retriever.retrieve_with_trace(
                routed, top_k=planned.k
            )
            retrieval_trace.append(
                {
                    "purpose": planned.purpose,
                    "query": planned.text,
                    "k": planned.k,
                    **trace,
                }
            )
            for doc in retrieved:
                if doc["id"] not in seen:
                    seen.add(doc["id"])
                    docs.append(doc)
        snippets: list[KnowledgeSnippet] = []
        for doc in docs:
            payload = doc.get("payload", {})
            meta = doc.get("meta", {})
            if meta.get("kind") == "action":
                content = (
                    f"动作：{payload.get('name', '')}。"
                    f"目标：{'、'.join(payload.get('target', []))}。"
                    f"辅助：{'、'.join(payload.get('assist', []))}。"
                    f"类型：{payload.get('type', '')}。"
                    f"要点：{payload.get('cues', '')}。"
                    f"常见错误：{payload.get('errors', '')}。"
                    f"提示：{payload.get('tips', '')}。"
                )
            elif meta.get("kind") == "viewpoint":
                viewpoint = str(payload.get("viewpoint", "")).rstrip()
                viewpoint = viewpoint.rstrip("。")
                source_url = payload.get("source_url", "")
                source_status = payload.get("source_status", "")
                source_ref = ""
                if source_status in {"linked", "partial"} and source_url:
                    label = (
                        "视频级来源，时间点待核"
                        if source_status == "partial"
                        else "原视频"
                    )
                    source_ref = f"{label}：{source_url}。"
                content = (
                    f"训练观点（人物：{payload.get('speaker', '')}）："
                    f"{viewpoint}。"
                    f"关联动作：{meta.get('action_name', '')}。"
                    f"来源主题：{payload.get('title', '')}。"
                    f"平台：{payload.get('platform', '')}；"
                    f"时间点：{payload.get('timestamp', '')}。"
                    f"{source_ref}"
                    "这是个人观点，引用时必须说明说话者。"
                )
            else:
                content = (
                    f"肌肉：{payload.get('name', '')}。"
                    f"部位：{payload.get('group', '')}/"
                    f"{payload.get('sub_group', '')}。"
                    f"位置：{payload.get('location', '')}。"
                    f"功能：{payload.get('function', '')}。"
                )
            snippets.append(
                KnowledgeSnippet(
                    id=doc["id"],
                    name=meta.get("name", doc["id"]),
                    kind=meta.get("kind", ""),
                    part=meta.get("part", ""),
                    content=content,
                    speaker=(
                        payload.get("speaker", "")
                        if meta.get("kind") == "viewpoint"
                        else ""
                    ),
                    source_url=(
                        payload.get("source_url", "")
                        if meta.get("kind") == "viewpoint"
                        else ""
                    ),
                    source_status=(
                        payload.get("source_status", "")
                        if meta.get("kind") == "viewpoint"
                        else ""
                    ),
                    timestamp=(
                        payload.get("timestamp", "")
                        if meta.get("kind") == "viewpoint"
                        else ""
                    ),
                )
            )
        return KnowledgeSearchResult(
            snippets=snippets,
            trace={
                "planned_queries": len(planned_queries),
                "retrievals": retrieval_trace,
                "source_ids": [item.id for item in snippets],
            },
        )
