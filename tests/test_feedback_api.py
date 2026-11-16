from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.chat.analytics import SQLiteAnalyticsStore
from src.chat.api import analytics_router, router
from src.chat.knowledge import EmptyKnowledgeProvider
from src.chat.orchestrator import ChatOrchestrator
from src.chat.providers import ChatModel
from src.chat.session import SQLiteSessionStore


class OfflineModel(ChatModel):
    @property
    def available(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return "offline"

    def complete(self, messages):
        raise RuntimeError("offline")


class FeedbackApiTests(unittest.TestCase):
    def test_chat_feedback_and_summary_are_linked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "feedback.sqlite3"
            service = ChatOrchestrator(
                session_store=SQLiteSessionStore(database),
                knowledge_provider=EmptyKnowledgeProvider(),
                model=OfflineModel(),
                analytics=SQLiteAnalyticsStore(database),
            )
            app = FastAPI()
            app.include_router(router)
            app.include_router(analytics_router)

            with patch("src.chat.api._orchestrator", service):
                client = TestClient(app)
                reply = client.post(
                    "/api/chat", json={"message": "你好"}
                ).json()
                self.assertTrue(reply["request_id"])
                self.assertEqual(reply["mode"], "local_fallback")

                saved = client.post(
                    "/api/feedback",
                    json={
                        "request_id": reply["request_id"],
                        "rating": -1,
                        "reason": "回答太笼统",
                        "comment": "端到端测试",
                        "user_key": "test_user",
                    },
                )
                self.assertEqual(saved.status_code, 200)

                summary = client.get(
                    "/api/chat/analytics/summary"
                ).json()
                self.assertEqual(summary["feedback_total"], 1)
                self.assertEqual(summary["negative"], 1)
                self.assertEqual(summary["events"], 1)


if __name__ == "__main__":
    unittest.main()
