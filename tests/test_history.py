from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.chat.analytics import SQLiteAnalyticsStore
from src.chat.contracts import TrainingProfile
from src.chat.session import SQLiteSessionStore


class SQLiteSessionStoreTests(unittest.TestCase):
    def test_persistence_search_rename_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.sqlite3"
            store = SQLiteSessionStore(path)
            session = store.get_or_create()
            session.profile.merge(
                TrainingProfile(
                    goal="增肌",
                    days_per_week=3,
                    equipment=["哑铃"],
                )
            )
            store.append_message(
                session,
                "user",
                "家里有哑铃，想增肌，每周三天",
                request_id="req_history_1",
            )
            store.append_message(
                session,
                "assistant",
                "已记录你的训练资料。",
                sources=[
                    {
                        "id": "action_test",
                        "name": "测试动作",
                        "source_url": "https://example.com/video",
                    }
                ],
            )

            self.assertNotEqual(session.title, "新对话")
            self.assertEqual(len(store.list_sessions()), 1)
            self.assertEqual(len(store.list_sessions("哑铃")), 1)
            self.assertTrue(store.rename(session.id, "三天增肌计划"))

            reopened = SQLiteSessionStore(path)
            restored = reopened.get(session.id)
            self.assertIsNotNone(restored)
            self.assertEqual(restored.title, "三天增肌计划")
            self.assertEqual(restored.profile.goal, "增肌")
            self.assertEqual(len(restored.messages), 2)
            self.assertEqual(
                restored.messages[0].request_id, "req_history_1"
            )
            self.assertIsNotNone(restored.messages[0].id)
            self.assertEqual(
                restored.messages[1].sources[0]["id"],
                "action_test",
            )

            self.assertTrue(reopened.delete(session.id))
            self.assertIsNone(reopened.get(session.id))

    def test_session_ownership_is_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "owners.sqlite3"
            store = SQLiteSessionStore(path)
            session = store.get_or_create(owner_id="owner_a")
            store.append_message(session, "user", "A 的私有对话")

            self.assertIsNone(store.get(session.id, "owner_b"))
            self.assertEqual(store.list_sessions(owner_id="owner_b"), [])
            self.assertFalse(
                store.rename(session.id, "越权改名", "owner_b")
            )
            self.assertFalse(store.delete(session.id, "owner_b"))
            with self.assertRaises(PermissionError):
                store.get_or_create(session.id, "owner_b")

            self.assertIsNotNone(store.get(session.id, "owner_a"))
            self.assertEqual(len(store.list_sessions(owner_id="owner_a")), 1)

    def test_legacy_conversation_is_claimed_by_saved_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.sqlite3"
            connection = sqlite3.connect(path)
            connection.executescript(
                """
                CREATE TABLE conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    profile_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    request_id TEXT
                );
                INSERT INTO conversations
                VALUES ('legacy-session', '旧对话', '{}',
                        '2026-01-01', '2026-01-01');
                """
            )
            connection.commit()
            connection.close()

            store = SQLiteSessionStore(path)
            claimed = store.get("legacy-session", "owner_a")
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed.owner_id, "owner_a")
            self.assertIsNone(store.get("legacy-session", "owner_b"))

    def test_feedback_is_linked_to_retrieval_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analytics.sqlite3"
            store = SQLiteAnalyticsStore(path)
            store.record_event(
                {
                    "request_id": "req_test_123",
                    "session_id": "session_1",
                    "answer_id": 7,
                    "query": "测试问题",
                    "intent": "knowledge",
                    "mode": "llm:test",
                    "model": "test",
                    "latency_ms": 120,
                    "input_tokens": 80,
                    "output_tokens": 40,
                    "final_ids": ["action_test"],
                    "sources": [{"id": "action_test"}],
                    "retrieval_trace": {"retrievals": []},
                }
            )
            store.add_feedback(
                request_id="req_test_123",
                rating=-1,
                reason="没找到动作",
                comment="测试反馈",
                user_key="user_1",
            )
            store.add_feedback(
                request_id="req_test_123",
                rating=1,
                user_key="user_1",
            )
            summary = store.summary()
            self.assertEqual(summary["feedback_total"], 1)
            self.assertEqual(summary["positive"], 1)
            self.assertEqual(summary["negative"], 0)
            self.assertEqual(summary["events"], 1)
            self.assertEqual(summary["input_tokens"], 80)
            self.assertEqual(summary["output_tokens"], 40)
            self.assertEqual(summary["intents"][0]["intent"], "knowledge")

    def test_analytics_are_scoped_and_deleted_with_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scoped_analytics.sqlite3"
            store = SQLiteAnalyticsStore(path)
            store.record_event(
                {
                    "request_id": "req_owner_a",
                    "owner_id": "owner_a",
                    "session_id": "session_a",
                    "query": "A 的查询",
                }
            )
            store.record_event(
                {
                    "request_id": "req_owner_b",
                    "owner_id": "owner_b",
                    "session_id": "session_b",
                    "query": "B 的查询",
                }
            )
            store.record_event(
                {
                    "request_id": "req_legacy_a",
                    "owner_id": "legacy",
                    "session_id": "session_a",
                    "query": "旧版本查询",
                }
            )
            store.add_feedback(
                request_id="req_owner_a",
                rating=1,
                owner_id="owner_a",
                user_key="owner_a",
            )

            self.assertEqual(
                store.summary(owner_id="owner_a")["events"], 1
            )
            self.assertEqual(
                store.summary(owner_id="owner_b")["events"], 1
            )
            self.assertEqual(
                store.delete_for_session("session_a", "owner_a"), 3
            )
            owner_a = store.summary(owner_id="owner_a")
            self.assertEqual(owner_a["events"], 0)
            self.assertEqual(owner_a["feedback_total"], 0)
            self.assertEqual(
                store.summary(owner_id="owner_b")["events"], 1
            )


if __name__ == "__main__":
    unittest.main()
