from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from abc import ABC, abstractmethod
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from src.chat.contracts import TrainingProfile


DEFAULT_OWNER_ID = "local"
LEGACY_OWNER_ID = "legacy"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def derive_title(text: str) -> str:
    title = " ".join(text.strip().split())
    return (title[:28] + "…") if len(title) > 28 else title


@dataclass
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str
    created_at: str = field(default_factory=now_iso)
    id: int | None = None
    request_id: str | None = None
    sources: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
            "request_id": self.request_id,
            "sources": self.sources,
        }


@dataclass
class ChatSession:
    id: str
    owner_id: str = DEFAULT_OWNER_ID
    title: str = "新对话"
    profile: TrainingProfile = field(default_factory=TrainingProfile)
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def add(self, role: Literal["user", "assistant"], content: str) -> None:
        self.messages.append(ChatMessage(role=role, content=content))
        self.updated_at = now_iso()
        if role == "user" and self.title == "新对话":
            self.title = derive_title(content)

    def recent(self, limit: int = 12) -> list[ChatMessage]:
        return self.messages[-limit:]


@dataclass(frozen=True)
class ConversationSummary:
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    preview: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count,
            "preview": self.preview,
        }


class SessionStore(ABC):
    @abstractmethod
    def get(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> ChatSession | None:
        raise NotImplementedError

    @abstractmethod
    def get_or_create(
        self,
        session_id: str | None = None,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> ChatSession:
        raise NotImplementedError

    @abstractmethod
    def append_message(
        self,
        session: ChatSession,
        role: Literal["user", "assistant"],
        content: str,
        request_id: str | None = None,
        sources: list[dict] | None = None,
    ) -> ChatMessage:
        raise NotImplementedError

    @abstractmethod
    def list_sessions(
        self,
        query: str = "",
        limit: int = 100,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> list[ConversationSummary]:
        raise NotImplementedError

    @abstractmethod
    def rename(
        self,
        session_id: str,
        title: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> bool:
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    """Useful for tests and ephemeral deployments."""

    def __init__(self, max_sessions: int = 500):
        self.max_sessions = max_sessions
        self._sessions: dict[str, ChatSession] = {}
        self._lock = threading.RLock()
        self._message_seq = 0

    def _trim(self) -> None:
        while len(self._sessions) > self.max_sessions:
            oldest = min(
                self._sessions,
                key=lambda key: self._sessions[key].updated_at,
            )
            del self._sessions[oldest]

    def get(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> ChatSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.owner_id != owner_id:
                return None
            return session

    def get_or_create(
        self,
        session_id: str | None = None,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> ChatSession:
        with self._lock:
            if session_id and session_id in self._sessions:
                existing = self._sessions[session_id]
                if existing.owner_id != owner_id:
                    raise PermissionError("会话不存在")
                return existing
            new_id = session_id or uuid.uuid4().hex
            session = ChatSession(id=new_id, owner_id=owner_id)
            self._sessions[new_id] = session
            self._trim()
            return session

    def append_message(
        self,
        session,
        role,
        content,
        request_id=None,
        sources=None,
    ):
        with self._lock:
            self._message_seq += 1
            message = ChatMessage(
                role=role,
                content=content,
                id=self._message_seq,
                request_id=request_id,
                sources=list(sources or []),
            )
            session.messages.append(message)
            session.updated_at = message.created_at
            if role == "user" and session.title == "新对话":
                session.title = derive_title(content)
            return message

    def list_sessions(
        self,
        query="",
        limit=100,
        owner_id=DEFAULT_OWNER_ID,
    ):
        needle = query.strip().lower()
        with self._lock:
            sessions = sorted(
                (
                    session
                    for session in self._sessions.values()
                    if session.owner_id == owner_id
                ),
                key=lambda item: item.updated_at,
                reverse=True,
            )
            result = []
            for session in sessions:
                haystack = " ".join(
                    [session.title]
                    + [message.content for message in session.messages]
                ).lower()
                if needle and needle not in haystack:
                    continue
                preview = (
                    session.messages[-1].content if session.messages else ""
                )
                result.append(
                    ConversationSummary(
                        id=session.id,
                        title=session.title,
                        created_at=session.created_at,
                        updated_at=session.updated_at,
                        message_count=len(session.messages),
                        preview=preview[:80],
                    )
                )
                if len(result) >= limit:
                    break
            return result

    def rename(
        self,
        session_id: str,
        title: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.owner_id != owner_id:
                return False
            session.title = title.strip() or "新对话"
            session.updated_at = now_iso()
            return True

    def delete(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.owner_id != owner_id:
                return False
            return self._sessions.pop(session_id, None) is not None


class SQLiteSessionStore(SessionStore):
    """Persistent single-user conversation storage."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'legacy',
                    title TEXT NOT NULL DEFAULT '新对话',
                    profile_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    request_id TEXT,
                    sources_json TEXT,
                    FOREIGN KEY(conversation_id)
                        REFERENCES conversations(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id, id);
                CREATE INDEX IF NOT EXISTS idx_conversations_updated
                    ON conversations(updated_at DESC);
                """
            )
            conversation_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(conversations)"
                ).fetchall()
            }
            if "owner_id" not in conversation_columns:
                connection.execute(
                    "ALTER TABLE conversations "
                    "ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'legacy'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_owner_updated "
                "ON conversations(owner_id, updated_at DESC)"
            )
            message_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(messages)"
                ).fetchall()
            }
            if "request_id" not in message_columns:
                connection.execute(
                    "ALTER TABLE messages ADD COLUMN request_id TEXT"
                )
            if "sources_json" not in message_columns:
                connection.execute(
                    "ALTER TABLE messages ADD COLUMN sources_json TEXT"
                )
            connection.commit()

    def get(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> ChatSession | None:
        with self._lock, closing(self._connect()) as connection:
            conversation = connection.execute(
                "SELECT * FROM conversations "
                "WHERE id = ? AND owner_id = ?",
                (session_id, owner_id),
            ).fetchone()
            if conversation is None and owner_id != LEGACY_OWNER_ID:
                cursor = connection.execute(
                    "UPDATE conversations SET owner_id = ? "
                    "WHERE id = ? AND owner_id = ?",
                    (owner_id, session_id, LEGACY_OWNER_ID),
                )
                if cursor.rowcount:
                    connection.commit()
                    conversation = connection.execute(
                        "SELECT * FROM conversations "
                        "WHERE id = ? AND owner_id = ?",
                        (session_id, owner_id),
                    ).fetchone()
            if conversation is None:
                return None
            message_rows = connection.execute(
                "SELECT id, role, content, created_at, request_id, "
                "sources_json "
                "FROM messages "
                "WHERE conversation_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        profile_data = json.loads(conversation["profile_json"] or "{}")
        return ChatSession(
            id=conversation["id"],
            owner_id=conversation["owner_id"],
            title=conversation["title"],
            profile=TrainingProfile(**profile_data),
            messages=[
                ChatMessage(
                    role=row["role"],
                    content=row["content"],
                    created_at=row["created_at"],
                    id=row["id"],
                    request_id=row["request_id"],
                    sources=(
                        json.loads(row["sources_json"])
                        if row["sources_json"]
                        else []
                    ),
                )
                for row in message_rows
            ],
            created_at=conversation["created_at"],
            updated_at=conversation["updated_at"],
        )

    def get_or_create(
        self,
        session_id: str | None = None,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> ChatSession:
        if session_id:
            existing = self.get(session_id, owner_id)
            if existing is not None:
                return existing
        new_id = session_id or uuid.uuid4().hex
        timestamp = now_iso()
        with self._lock, closing(self._connect()) as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO conversations "
                "(id, owner_id, title, profile_json, created_at, updated_at) "
                "VALUES (?, ?, '新对话', '{}', ?, ?)",
                (new_id, owner_id, timestamp, timestamp),
            )
            if cursor.rowcount == 0:
                existing_owner = connection.execute(
                    "SELECT owner_id FROM conversations WHERE id = ?",
                    (new_id,),
                ).fetchone()
                if (
                    existing_owner is None
                    or existing_owner["owner_id"] != owner_id
                ):
                    raise PermissionError("会话不存在")
            connection.commit()
        if cursor.rowcount == 0:
            existing = self.get(new_id, owner_id)
            if existing is None:
                raise PermissionError("会话不存在")
            return existing
        return ChatSession(
            id=new_id,
            owner_id=owner_id,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def append_message(
        self,
        session,
        role,
        content,
        request_id=None,
        sources=None,
    ):
        message = ChatMessage(
            role=role,
            content=content,
            request_id=request_id,
            sources=list(sources or []),
        )
        new_title = (
            derive_title(content)
            if role == "user" and session.title == "新对话"
            else session.title
        )
        with self._lock, closing(self._connect()) as connection:
            cursor = connection.execute(
                "INSERT INTO messages "
                "(conversation_id, role, content, created_at, "
                "request_id, sources_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session.id,
                    role,
                    content,
                    message.created_at,
                    request_id,
                    json.dumps(
                        message.sources,
                        ensure_ascii=False,
                    )
                    if message.sources
                    else None,
                ),
            )
            message.id = int(cursor.lastrowid)
            connection.execute(
                "UPDATE conversations SET title = ?, profile_json = ?, "
                "updated_at = ? WHERE id = ? AND owner_id = ?",
                (
                    new_title,
                    json.dumps(
                        session.profile.to_dict(), ensure_ascii=False
                    ),
                    message.created_at,
                    session.id,
                    session.owner_id,
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] == 0:
                connection.rollback()
                raise PermissionError("会话不存在")
            connection.commit()
        session.messages.append(message)
        session.title = new_title
        session.updated_at = message.created_at
        return message

    def list_sessions(
        self,
        query="",
        limit=100,
        owner_id=DEFAULT_OWNER_ID,
    ):
        needle = f"%{query.strip()}%"
        sql = """
            SELECT
                c.id, c.title, c.created_at, c.updated_at,
                (SELECT COUNT(*) FROM messages m
                 WHERE m.conversation_id = c.id) AS message_count,
                COALESCE((
                    SELECT m.content FROM messages m
                    WHERE m.conversation_id = c.id
                    ORDER BY m.id DESC LIMIT 1
                ), '') AS preview
            FROM conversations c
            WHERE c.owner_id = ?
        """
        params: list = [owner_id]
        if query.strip():
            sql += """
                AND (c.title LIKE ? OR EXISTS (
                    SELECT 1 FROM messages m
                    WHERE m.conversation_id = c.id AND m.content LIKE ?
                ))
            """
            params.extend([needle, needle])
        sql += " ORDER BY c.updated_at DESC LIMIT ?"
        params.append(limit)
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(sql, params).fetchall()
        return [
            ConversationSummary(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                message_count=int(row["message_count"]),
                preview=row["preview"][:80],
            )
            for row in rows
        ]

    def rename(
        self,
        session_id: str,
        title: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> bool:
        title = title.strip() or "新对话"
        with self._lock, closing(self._connect()) as connection:
            cursor = connection.execute(
                "UPDATE conversations SET title = ?, updated_at = ? "
                "WHERE id = ? AND owner_id = ?",
                (title, now_iso(), session_id, owner_id),
            )
            connection.commit()
        return cursor.rowcount > 0

    def delete(
        self,
        session_id: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> bool:
        with self._lock, closing(self._connect()) as connection:
            cursor = connection.execute(
                "DELETE FROM conversations "
                "WHERE id = ? AND owner_id = ?",
                (session_id, owner_id),
            )
            connection.commit()
        return cursor.rowcount > 0
