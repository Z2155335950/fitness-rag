from __future__ import annotations

import json
import sqlite3
import threading
from abc import ABC, abstractmethod
from contextlib import closing
from pathlib import Path
from typing import Any

from src.chat.session import DEFAULT_OWNER_ID, now_iso


class AnalyticsStore(ABC):
    @abstractmethod
    def record_event(self, event: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_feedback(
        self,
        *,
        request_id: str,
        rating: int,
        reason: str = "",
        comment: str = "",
        user_key: str = "anonymous",
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def summary(
        self,
        days: int = 30,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def delete_for_session(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> int:
        raise NotImplementedError


class NoopAnalyticsStore(AnalyticsStore):
    def record_event(self, event: dict[str, Any]) -> None:
        return None

    def add_feedback(self, **kwargs) -> None:
        return None

    def summary(
        self,
        days: int = 30,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> dict:
        return {}

    def delete_for_session(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> int:
        return 0


class SQLiteAnalyticsStore(AnalyticsStore):
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS retrieval_events (
                    request_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'legacy',
                    session_id TEXT NOT NULL,
                    answer_id INTEGER,
                    query TEXT NOT NULL,
                    intent TEXT,
                    filters_json TEXT,
                    entities_json TEXT,
                    exact_ids_json TEXT,
                    reverse_ids_json TEXT,
                    vector_ids_json TEXT,
                    bm25_ids_json TEXT,
                    field_ids_json TEXT,
                    final_ids_json TEXT,
                    sources_json TEXT,
                    retrieval_trace_json TEXT,
                    model TEXT,
                    mode TEXT,
                    latency_ms INTEGER,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS answer_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL DEFAULT 'legacy',
                    session_id TEXT NOT NULL,
                    answer_id INTEGER,
                    rating INTEGER NOT NULL CHECK(rating IN (-1, 1)),
                    reason TEXT NOT NULL DEFAULT '',
                    comment TEXT NOT NULL DEFAULT '',
                    user_key TEXT NOT NULL DEFAULT 'anonymous',
                    created_at TEXT NOT NULL,
                    UNIQUE(request_id, user_key)
                );
                CREATE INDEX IF NOT EXISTS idx_feedback_created
                    ON answer_feedback(created_at DESC);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(retrieval_events)"
                ).fetchall()
            }
            if "input_tokens" not in columns:
                connection.execute(
                    "ALTER TABLE retrieval_events "
                    "ADD COLUMN input_tokens INTEGER NOT NULL DEFAULT 0"
                )
            if "output_tokens" not in columns:
                connection.execute(
                    "ALTER TABLE retrieval_events "
                    "ADD COLUMN output_tokens INTEGER NOT NULL DEFAULT 0"
                )
            if "owner_id" not in columns:
                connection.execute(
                    "ALTER TABLE retrieval_events "
                    "ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'legacy'"
                )
            feedback_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(answer_feedback)"
                ).fetchall()
            }
            if "owner_id" not in feedback_columns:
                connection.execute(
                    "ALTER TABLE answer_feedback "
                    "ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'legacy'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_session_owner "
                "ON retrieval_events(owner_id, session_id)"
            )
            connection.commit()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value or [], ensure_ascii=False)

    def record_event(self, event: dict[str, Any]) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO retrieval_events (
                    request_id, owner_id, session_id, answer_id, query, intent,
                    filters_json, entities_json, exact_ids_json,
                    reverse_ids_json, vector_ids_json, bm25_ids_json,
                    field_ids_json, final_ids_json, sources_json,
                    retrieval_trace_json, model, mode, latency_ms,
                    input_tokens, output_tokens, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["request_id"],
                    event.get("owner_id", DEFAULT_OWNER_ID),
                    event["session_id"],
                    event.get("answer_id"),
                    event["query"],
                    event.get("intent", ""),
                    self._json(event.get("filters")),
                    self._json(event.get("entities")),
                    self._json(event.get("exact_ids")),
                    self._json(event.get("reverse_ids")),
                    self._json(event.get("vector_ids")),
                    self._json(event.get("bm25_ids")),
                    self._json(event.get("field_ids")),
                    self._json(event.get("final_ids")),
                    self._json(event.get("sources")),
                    json.dumps(
                        event.get("retrieval_trace", {}),
                        ensure_ascii=False,
                    ),
                    event.get("model", ""),
                    event.get("mode", ""),
                    int(event.get("latency_ms", 0)),
                    int(event.get("input_tokens", 0)),
                    int(event.get("output_tokens", 0)),
                    event.get("created_at") or now_iso(),
                ),
            )
            connection.commit()

    def add_feedback(
        self,
        *,
        request_id: str,
        rating: int,
        reason: str = "",
        comment: str = "",
        user_key: str = "anonymous",
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> None:
        if rating not in {-1, 1}:
            raise ValueError("rating 必须是 1 或 -1")
        with self._lock, closing(self._connect()) as connection:
            event = connection.execute(
                "SELECT session_id, answer_id FROM retrieval_events "
                "WHERE request_id = ? AND owner_id = ?",
                (request_id, owner_id),
            ).fetchone()
            if event is None:
                raise KeyError("request_id 不存在")
            connection.execute(
                """
                INSERT INTO answer_feedback (
                    request_id, owner_id, session_id, answer_id, rating,
                    reason, comment, user_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(request_id, user_key) DO UPDATE SET
                    rating=excluded.rating,
                    reason=excluded.reason,
                    comment=excluded.comment,
                    created_at=excluded.created_at
                """,
                (
                    request_id,
                    owner_id,
                    event["session_id"],
                    event["answer_id"],
                    rating,
                    reason.strip()[:120],
                    comment.strip()[:1000],
                    user_key.strip()[:80] or "anonymous",
                    now_iso(),
                ),
            )
            connection.commit()

    def summary(
        self,
        days: int = 30,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> dict:
        cutoff = f"-{max(days, 1)} days"
        with self._lock, closing(self._connect()) as connection:
            feedback = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) AS positive,
                       SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) AS negative
                FROM answer_feedback
                WHERE julianday(created_at) >= julianday('now', ?)
                  AND owner_id = ?
                """,
                (cutoff, owner_id),
            ).fetchone()
            events = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       AVG(latency_ms) AS avg_latency,
                       SUM(input_tokens) AS input_tokens,
                       SUM(output_tokens) AS output_tokens
                FROM retrieval_events
                WHERE julianday(created_at) >= julianday('now', ?)
                  AND owner_id = ?
                """,
                (cutoff, owner_id),
            ).fetchone()
            reasons = connection.execute(
                """
                SELECT reason, COUNT(*) AS count
                FROM answer_feedback
                WHERE rating = -1 AND reason <> ''
                  AND julianday(created_at) >= julianday('now', ?)
                  AND owner_id = ?
                GROUP BY reason ORDER BY count DESC
                """,
                (cutoff, owner_id),
            ).fetchall()
            intents = connection.execute(
                """
                SELECT e.intent,
                       COUNT(*) AS total,
                       SUM(CASE WHEN f.rating = 1 THEN 1 ELSE 0 END) AS positive,
                       SUM(CASE WHEN f.rating = -1 THEN 1 ELSE 0 END) AS negative
                FROM retrieval_events e
                JOIN answer_feedback f ON f.request_id = e.request_id
                WHERE julianday(f.created_at) >= julianday('now', ?)
                  AND e.owner_id = ? AND f.owner_id = e.owner_id
                GROUP BY e.intent ORDER BY total DESC
                """,
                (cutoff, owner_id),
            ).fetchall()
        total = int(feedback["total"] or 0)
        positive = int(feedback["positive"] or 0)
        negative = int(feedback["negative"] or 0)
        return {
            "days": days,
            "feedback_total": total,
            "positive": positive,
            "negative": negative,
            "positive_rate": positive / total if total else 0.0,
            "events": int(events["total"] or 0),
            "average_latency_ms": round(
                float(events["avg_latency"] or 0.0), 2
            ),
            "input_tokens": int(events["input_tokens"] or 0),
            "output_tokens": int(events["output_tokens"] or 0),
            "negative_reasons": [
                {"reason": row["reason"], "count": int(row["count"])}
                for row in reasons
            ],
            "intents": [
                {
                    "intent": row["intent"],
                    "total": int(row["total"]),
                    "positive": int(row["positive"] or 0),
                    "negative": int(row["negative"] or 0),
                }
                for row in intents
            ],
        }

    def delete_for_session(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> int:
        with self._lock, closing(self._connect()) as connection:
            feedback = connection.execute(
                "DELETE FROM answer_feedback "
                "WHERE session_id = ? "
                "AND owner_id IN (?, 'legacy')",
                (session_id, owner_id),
            ).rowcount
            events = connection.execute(
                "DELETE FROM retrieval_events "
                "WHERE session_id = ? "
                "AND owner_id IN (?, 'legacy')",
                (session_id, owner_id),
            ).rowcount
            connection.commit()
        return max(feedback, 0) + max(events, 0)
