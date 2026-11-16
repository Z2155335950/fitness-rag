from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.chat.api import router
from src.chat.page import CHAT_PAGE


class SessionIdValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_chat_rejects_html_attribute_injection(self) -> None:
        response = self.client.post(
            "/api/chat",
            json={
                "message": "你好",
                "session_id": 'x" onmouseover="alert(1)',
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_history_rejects_invalid_session_id(self) -> None:
        response = self.client.get("/api/chat/bad")
        self.assertEqual(response.status_code, 422)

    def test_frontend_escapes_dynamic_html_attributes(self) -> None:
        self.assertIn("function escAttr(value)", CHAT_PAGE)
        self.assertIn(
            'data-id="${escAttr(item.id)}"',
            CHAT_PAGE,
        )
        self.assertIn(
            "encodeURIComponent(sessionId)",
            CHAT_PAGE,
        )
        self.assertIn("function renderMarkdown(value)", CHAT_PAGE)
        self.assertIn("function safeUrl(value)", CHAT_PAGE)
        self.assertIn("item.sources || []", CHAT_PAGE)


if __name__ == "__main__":
    unittest.main()
