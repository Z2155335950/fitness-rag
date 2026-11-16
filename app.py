from __future__ import annotations

from threading import Lock

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.chat.api import analytics_router, router as chat_router
from src.chat.auth import current_owner
from src.chat.page import CHAT_PAGE
from src.config import DB_DIR
from src.index.health import check_index
from src.rag import FitnessRAG


app = FastAPI(
    title="网红训练法",
    description="训练策略与动作知识对话系统",
    version="2.0.0",
)
app.include_router(chat_router)
app.include_router(analytics_router)

_service: FitnessRAG | None = None
_service_lock = Lock()


def get_service() -> FitnessRAG:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = FitnessRAG()
    return _service


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    top_k: int = Field(default=5, ge=1, le=10)


@app.get("/health")
def health() -> dict:
    return check_index(DB_DIR)


@app.post("/api/query")
def query(request: QueryRequest) -> dict:
    """Backward-compatible single-turn retrieval endpoint."""
    try:
        return get_service().query(request.query, request.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/actions/{action_id}/viewpoints")
def action_viewpoints(action_id: str) -> dict:
    viewpoints = get_service().action_viewpoints(action_id)
    return {
        "action_id": action_id,
        "viewpoint_count": len(viewpoints),
        "related_viewpoints": viewpoints,
    }


@app.get("/", response_class=HTMLResponse)
def home(_owner_id: str = Depends(current_owner)) -> str:
    return CHAT_PAGE
