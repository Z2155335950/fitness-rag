from __future__ import annotations

import threading
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from src.chat.analytics import SQLiteAnalyticsStore
from src.chat.auth import current_owner
from src.chat.knowledge import RAGKnowledgeProvider
from src.chat.orchestrator import ChatOrchestrator
from src.chat.providers import create_chat_model
from src.chat.session import SQLiteSessionStore
from src.config import CHAT_DB_PATH, DB_DIR
from src.index.health import check_index


router = APIRouter(prefix="/api/chat", tags=["chat"])
analytics_router = APIRouter(tags=["analytics"])

_orchestrator: ChatOrchestrator | None = None
_lock = threading.Lock()
SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{16,64}$"


def get_orchestrator() -> ChatOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        with _lock:
            if _orchestrator is None:
                _orchestrator = ChatOrchestrator(
                    session_store=SQLiteSessionStore(CHAT_DB_PATH),
                    knowledge_provider=RAGKnowledgeProvider(),
                    model=create_chat_model(),
                    analytics=SQLiteAnalyticsStore(CHAT_DB_PATH),
                )
    return _orchestrator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(
        default=None,
        max_length=64,
        pattern=SESSION_ID_PATTERN,
    )


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=80)
    rating: Literal[-1, 1]
    reason: str = Field(default="", max_length=120)
    comment: str = Field(default="", max_length=1000)
    user_key: str = Field(default="anonymous", max_length=80)


@router.get("/status")
def status(
    _owner_id: str = Depends(current_owner),
) -> dict:
    service = get_orchestrator()
    index = check_index(DB_DIR)
    return {
        "ready": index["ready"],
        "index_status": index["status"],
        "index_integrity": index["integrity"],
        "llm_configured": service.model.available,
        "model": service.model.name,
        "mode": "llm" if service.model.available else "local_fallback",
    }


@router.get("/conversations")
def conversations(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=100, ge=1, le=500),
    owner_id: str = Depends(current_owner),
) -> dict:
    summaries = get_orchestrator().list_conversations(
        q, limit, owner_id
    )
    return {
        "conversations": [item.to_dict() for item in summaries],
        "query": q,
    }


@router.post("/conversations")
def create_conversation(
    owner_id: str = Depends(current_owner),
) -> dict:
    session = get_orchestrator().sessions.get_or_create(
        owner_id=owner_id
    )
    return {
        "session_id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": [],
    }


@router.patch("/conversations/{session_id}")
def rename_conversation(
    request: RenameRequest,
    session_id: Annotated[str, Path(pattern=SESSION_ID_PATTERN)],
    owner_id: str = Depends(current_owner),
) -> dict:
    renamed = get_orchestrator().rename(
        session_id, request.title, owner_id
    )
    if not renamed:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"renamed": True, "session_id": session_id, "title": request.title}


@router.post("")
def chat(
    request: ChatRequest,
    owner_id: str = Depends(current_owner),
) -> dict:
    try:
        reply = get_orchestrator().chat(
            request.message,
            request.session_id,
            owner_id,
        )
        return {
            "answer": reply.answer,
            "session_id": reply.session_id,
            "request_id": reply.request_id,
            "answer_id": reply.answer_id,
            "mode": reply.mode,
            "intent": reply.intent,
            "sources": reply.sources,
            "citations": reply.citations,
            "profile": reply.profile,
            "missing_fields": reply.missing_fields,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc


@analytics_router.post("/api/feedback")
def feedback(
    request: FeedbackRequest,
    owner_id: str = Depends(current_owner),
) -> dict:
    try:
        get_orchestrator().feedback(
            owner_id=owner_id,
            request_id=request.request_id,
            rating=request.rating,
            reason=request.reason,
            comment=request.comment,
            user_key=owner_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"saved": True, "request_id": request.request_id}


@analytics_router.get("/api/chat/analytics/summary")
def analytics_summary(
    days: int = Query(default=30, ge=1, le=365),
    owner_id: str = Depends(current_owner),
) -> dict:
    return get_orchestrator().analytics_summary(days, owner_id)


@router.get("/{session_id}")
def history(
    session_id: Annotated[str, Path(pattern=SESSION_ID_PATTERN)],
    owner_id: str = Depends(current_owner),
) -> dict:
    session = get_orchestrator().history(session_id, owner_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {
        "session_id": session.id,
        "profile": session.profile.to_dict(),
        "messages": [message.to_dict() for message in session.messages],
    }


@router.delete("/{session_id}")
def reset(
    session_id: Annotated[str, Path(pattern=SESSION_ID_PATTERN)],
    owner_id: str = Depends(current_owner),
) -> dict:
    deleted = get_orchestrator().reset(session_id, owner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"deleted": True, "session_id": session_id}
