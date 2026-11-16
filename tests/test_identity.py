from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import app as web_app
from src.chat.analytics import SQLiteAnalyticsStore
from src.chat.api import analytics_router, router
from src.chat.auth import issue_owner_token, verify_owner_token
from src.chat.contracts import KnowledgeSearchResult, KnowledgeSnippet
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


class SourceKnowledge(EmptyKnowledgeProvider):
    def search(self, message, profile, intent, top_k=6):
        return KnowledgeSearchResult(
            snippets=[
                KnowledgeSnippet(
                    id="action_source_test",
                    name="来源测试动作",
                    kind="action",
                    part="胸部",
                    content="动作：来源测试动作。要点：保持稳定。",
                    source_url="https://example.com/source",
                    source_status="linked",
                )
            ]
        )


class OwnerTokenTests(unittest.TestCase):
    def test_tampered_owner_token_is_rejected(self) -> None:
        owner = "user_" + "a" * 32
        token = issue_owner_token(owner, b"test-secret")
        self.assertEqual(verify_owner_token(token, b"test-secret"), owner)
        self.assertIsNone(
            verify_owner_token(token[:-1] + "x", b"test-secret")
        )

    def test_home_page_issues_owner_cookie(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_SECRET_KEY": "home-test-secret"},
            clear=False,
        ):
            client = TestClient(web_app)
            response = client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertIn("fitness_owner", response.cookies)


class ConversationOwnershipApiTests(unittest.TestCase):
    def test_history_restores_source_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "sources.sqlite3"
            service = ChatOrchestrator(
                session_store=SQLiteSessionStore(database),
                knowledge_provider=SourceKnowledge(),
                model=OfflineModel(),
                analytics=SQLiteAnalyticsStore(database),
            )
            app = FastAPI()
            app.include_router(router)
            app.include_router(analytics_router)

            with patch.dict(
                os.environ,
                {"APP_SECRET_KEY": "source-test-secret"},
                clear=False,
            ):
                with patch("src.chat.api._orchestrator", service):
                    client = TestClient(app)
                    reply = client.post(
                        "/api/chat",
                        json={"message": "推荐几个练胸动作"},
                    ).json()
                    history = client.get(
                        f"/api/chat/{reply['session_id']}"
                    ).json()

            assistant = history["messages"][-1]
            self.assertEqual(
                assistant["sources"][0]["source_url"],
                "https://example.com/source",
            )

    def test_browsers_cannot_access_each_others_conversations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "identity.sqlite3"
            service = ChatOrchestrator(
                session_store=SQLiteSessionStore(database),
                knowledge_provider=EmptyKnowledgeProvider(),
                model=OfflineModel(),
                analytics=SQLiteAnalyticsStore(database),
            )
            app = FastAPI()
            app.include_router(router)
            app.include_router(analytics_router)

            environment = {
                "APP_SECRET_KEY": "identity-test-secret",
                "APP_COOKIE_SECURE": "false",
            }
            with patch.dict(os.environ, environment, clear=False):
                with patch("src.chat.api._orchestrator", service):
                    owner_a = TestClient(app)
                    owner_b = TestClient(app)
                    reply = owner_a.post(
                        "/api/chat",
                        json={"message": "你好"},
                    ).json()
                    session_id = reply["session_id"]

                    self.assertEqual(
                        owner_b.get(
                            f"/api/chat/{session_id}"
                        ).status_code,
                        404,
                    )
                    self.assertEqual(
                        owner_b.patch(
                            f"/api/chat/conversations/{session_id}",
                            json={"title": "越权改名"},
                        ).status_code,
                        404,
                    )
                    self.assertEqual(
                        owner_b.delete(
                            f"/api/chat/{session_id}"
                        ).status_code,
                        404,
                    )
                    self.assertEqual(
                        owner_b.get(
                            "/api/chat/conversations"
                        ).json()["conversations"],
                        [],
                    )

                    cross_feedback = owner_b.post(
                        "/api/feedback",
                        json={
                            "request_id": reply["request_id"],
                            "rating": 1,
                            "user_key": "spoofed-user",
                        },
                    )
                    self.assertEqual(cross_feedback.status_code, 404)

                    own_feedback = owner_a.post(
                        "/api/feedback",
                        json={
                            "request_id": reply["request_id"],
                            "rating": 1,
                        },
                    )
                    self.assertEqual(own_feedback.status_code, 200)

    def test_delete_removes_conversation_and_analytics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "delete.sqlite3"
            service = ChatOrchestrator(
                session_store=SQLiteSessionStore(database),
                knowledge_provider=EmptyKnowledgeProvider(),
                model=OfflineModel(),
                analytics=SQLiteAnalyticsStore(database),
            )
            app = FastAPI()
            app.include_router(router)
            app.include_router(analytics_router)

            with patch.dict(
                os.environ,
                {"APP_SECRET_KEY": "delete-test-secret"},
                clear=False,
            ):
                with patch("src.chat.api._orchestrator", service):
                    client = TestClient(app)
                    reply = client.post(
                        "/api/chat",
                        json={"message": "敏感训练问题"},
                    ).json()
                    session_id = reply["session_id"]
                    feedback = client.post(
                        "/api/feedback",
                        json={
                            "request_id": reply["request_id"],
                            "rating": -1,
                            "comment": "敏感备注",
                        },
                    )
                    self.assertEqual(feedback.status_code, 200)

                    deleted = client.delete(
                        f"/api/chat/{session_id}"
                    )
                    self.assertEqual(deleted.status_code, 200)
                    self.assertEqual(
                        client.get(
                            f"/api/chat/{session_id}"
                        ).status_code,
                        404,
                    )
                    summary = client.get(
                        "/api/chat/analytics/summary"
                    ).json()
                    self.assertEqual(summary["events"], 0)
                    self.assertEqual(summary["feedback_total"], 0)

                    connection = sqlite3.connect(database)
                    event_count = connection.execute(
                        "SELECT COUNT(*) FROM retrieval_events "
                        "WHERE session_id = ?",
                        (session_id,),
                    ).fetchone()[0]
                    feedback_count = connection.execute(
                        "SELECT COUNT(*) FROM answer_feedback "
                        "WHERE session_id = ?",
                        (session_id,),
                    ).fetchone()[0]
                    connection.close()
                    self.assertEqual(event_count, 0)
                    self.assertEqual(feedback_count, 0)


if __name__ == "__main__":
    unittest.main()
