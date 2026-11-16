from __future__ import annotations

import logging
import threading
import time
import uuid

from src.chat.analytics import AnalyticsStore, NoopAnalyticsStore
from src.chat.citations import (
    NO_EVIDENCE_ANSWER,
    cited_records,
    cited_sources,
    requires_grounding,
    validate_grounded_answer,
)
from src.chat.contracts import (
    ChatReply,
    ConversationIntent,
    KnowledgeSearchResult,
    KnowledgeSnippet,
)
from src.chat.fallback import FallbackResponder
from src.chat.knowledge import KnowledgeProvider
from src.chat.profile import ProfileExtractor
from src.chat.prompts import build_messages
from src.chat.providers import ChatModel
from src.chat.session import (
    DEFAULT_OWNER_ID,
    ChatSession,
    SessionStore,
)


logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """Coordinates modules; it contains no retrieval or model-specific details."""

    def __init__(
        self,
        *,
        session_store: SessionStore,
        knowledge_provider: KnowledgeProvider,
        model: ChatModel,
        extractor: ProfileExtractor | None = None,
        fallback: FallbackResponder | None = None,
        analytics: AnalyticsStore | None = None,
    ):
        self.sessions = session_store
        self.knowledge = knowledge_provider
        self.model = model
        self.extractor = extractor or ProfileExtractor()
        self.fallback = fallback or FallbackResponder()
        self.analytics = analytics or NoopAnalyticsStore()
        self._session_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _session_lock(self, session_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._session_locks.setdefault(
                session_id, threading.Lock()
            )

    def _effective_intent(
        self, session: ChatSession, intent: ConversationIntent
    ) -> ConversationIntent:
        if (
            session.profile.plan_requested
            and intent == ConversationIntent.PROFILE_UPDATE
        ):
            return ConversationIntent.PLAN
        return intent

    def chat(
        self,
        message: str,
        session_id: str | None = None,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> ChatReply:
        message = message.strip()
        if not message:
            raise ValueError("消息不能为空")
        started = time.perf_counter()
        request_id = uuid.uuid4().hex

        session = self.sessions.get_or_create(session_id, owner_id)
        with self._session_lock(session.id):
            turn = self.extractor.extract(message)
            session.profile.merge(turn.profile_update)
            intent = self._effective_intent(session, turn.intent)
            self.sessions.append_message(
                session, "user", message, request_id=request_id
            )

            snippets: list[KnowledgeSnippet] = []
            knowledge_result = KnowledgeSearchResult()
            should_retrieve = (
                turn.should_retrieve or intent == ConversationIntent.PLAN
            )
            if should_retrieve:
                try:
                    knowledge_result = self.knowledge.search(
                        message, session.profile, intent, top_k=7
                    )
                    snippets = knowledge_result.snippets
                except Exception:
                    logger.exception("知识检索失败，继续使用对话层")

            mode = "local_fallback"
            input_tokens = output_tokens = 0
            grounding_required = requires_grounding(
                intent, session.profile
            )
            used_model = False
            if turn.safety_flag:
                answer = self.fallback.respond(
                    message,
                    session.profile,
                    intent,
                    snippets,
                    True,
                )
                mode = (
                    "safety_fallback"
                    if self.model.available
                    else "local_fallback"
                )
            elif grounding_required and not snippets:
                answer = NO_EVIDENCE_ANSWER
                mode = (
                    "grounding_fallback"
                    if self.model.available
                    else "local_fallback"
                )
            elif self.model.available:
                try:
                    answer = self.model.complete(
                        build_messages(session, snippets)
                    )
                    mode = f"llm:{self.model.name}"
                    used_model = True
                    usage = getattr(self.model, "last_usage", {})
                    input_tokens = int(usage.get("input_tokens", 0))
                    output_tokens = int(usage.get("output_tokens", 0))
                except Exception:
                    logger.exception("对话模型调用失败，切换到本地回答")
                    answer = self.fallback.respond(
                        message,
                        session.profile,
                        intent,
                        snippets,
                        turn.safety_flag,
                    )
            else:
                answer = self.fallback.respond(
                    message,
                    session.profile,
                    intent,
                    snippets,
                    turn.safety_flag,
                )

            cited_refs: list[int] = []
            if grounding_required and snippets:
                valid, cited_refs = validate_grounded_answer(
                    answer, snippets
                )
                if not valid:
                    logger.warning(
                        "模型回答缺少有效引用，切换为本地文档回答"
                    )
                    answer = self.fallback.respond(
                        message,
                        session.profile,
                        intent,
                        snippets,
                        turn.safety_flag,
                    )
                    if used_model:
                        mode = "grounding_fallback"
                    valid, cited_refs = validate_grounded_answer(
                        answer, snippets
                    )
                if not valid:
                    answer = NO_EVIDENCE_ANSWER
                    cited_refs = []
                    mode = "grounding_fallback"

            source_dicts = cited_sources(cited_refs, snippets)
            citation_records = cited_records(cited_refs, snippets)
            answer_message = self.sessions.append_message(
                session,
                "assistant",
                answer,
                request_id=request_id,
                sources=source_dicts,
            )
            latency_ms = round(
                (time.perf_counter() - started) * 1000
            )
            retrievals = knowledge_result.trace.get("retrievals", [])
            first_retrieval = retrievals[0] if retrievals else {}
            self._record_analytics(
                request_id=request_id,
                owner_id=owner_id,
                session_id=session.id,
                answer_id=answer_message.id,
                message=message,
                intent=intent,
                filters=first_retrieval.get("filters", {}),
                entities=first_retrieval.get("entities", []),
                snippets=snippets,
                sources=source_dicts,
                retrieval_trace=knowledge_result.trace,
                mode=mode,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            return ChatReply(
                answer=answer,
                session_id=session.id,
                mode=mode,
                intent=intent.value,
                request_id=request_id,
                answer_id=answer_message.id,
                sources=source_dicts,
                citations=citation_records,
                profile=session.profile.to_dict(),
                missing_fields=session.profile.missing_plan_fields(),
            )

    def _record_analytics(
        self,
        *,
        request_id,
        owner_id,
        session_id,
        answer_id,
        message,
        intent,
        filters,
        entities,
        snippets,
        sources,
        retrieval_trace,
        mode,
        latency_ms,
        input_tokens,
        output_tokens,
    ) -> None:
        def unique_channel(name: str) -> list[str]:
            values = []
            for retrieval in retrieval_trace.get("retrievals", []):
                for value in retrieval.get(name, []):
                    if value not in values:
                        values.append(value)
            return values

        try:
            self.analytics.record_event(
                {
                    "request_id": request_id,
                    "owner_id": owner_id,
                    "session_id": session_id,
                    "answer_id": answer_id,
                    "query": message,
                    "intent": intent.value,
                    "filters": filters,
                    "entities": entities,
                    "exact_ids": unique_channel("exact_ids"),
                    "reverse_ids": unique_channel("reverse_ids"),
                    "vector_ids": unique_channel("vector_ids"),
                    "bm25_ids": unique_channel("bm25_ids"),
                    "field_ids": unique_channel("field_ids"),
                    "final_ids": [item.id for item in snippets],
                    "sources": sources,
                    "retrieval_trace": retrieval_trace,
                    "model": self.model.name if self.model.available else "local",
                    "mode": mode,
                    "latency_ms": latency_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }
            )
        except Exception:
            logger.exception("反馈埋点写入失败，不影响聊天")

    def history(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> ChatSession | None:
        return self.sessions.get(session_id, owner_id)

    def list_conversations(
        self,
        query: str = "",
        limit: int = 100,
        owner_id: str = DEFAULT_OWNER_ID,
    ):
        return self.sessions.list_sessions(query, limit, owner_id)

    def rename(
        self,
        session_id: str,
        title: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> bool:
        return self.sessions.rename(session_id, title, owner_id)

    def reset(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> bool:
        with self._session_lock(session_id):
            purged = self.analytics.delete_for_session(
                session_id, owner_id
            )
            deleted = self.sessions.delete(session_id, owner_id)
        return deleted or purged > 0

    def feedback(
        self,
        owner_id: str = DEFAULT_OWNER_ID,
        **kwargs,
    ) -> None:
        kwargs["owner_id"] = owner_id
        self.analytics.add_feedback(**kwargs)

    def analytics_summary(
        self,
        days: int = 30,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> dict:
        return self.analytics.summary(days, owner_id)
