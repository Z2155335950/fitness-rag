from __future__ import annotations

import unittest

from src.query.schema import Intent, RoutedQuery
from src.rag import Answerer


class AnswererTests(unittest.TestCase):
    def test_action_answer_uses_knowledge_fields(self) -> None:
        action = {
            "id": "action_test",
            "name": "测试深蹲",
            "target": ["股四头肌"],
            "assist": ["臀大肌"],
            "type": "复合动作",
            "cues": "下蹲时保持膝盖方向。",
            "errors": "膝盖内扣。",
            "tips": "先用轻重量。",
        }
        routed = RoutedQuery("测试深蹲怎么做", [], Intent.ACTION_DETAIL)
        result = Answerer.compose(
            routed.raw,
            routed,
            [
                {
                    "id": action["id"],
                    "payload": action,
                    "meta": {"kind": "action", "name": action["name"]},
                }
            ],
        )
        self.assertIn("测试深蹲", result["answer"])
        self.assertIn("下蹲时保持膝盖方向", result["answer"])
        self.assertEqual(result["sources"][0]["id"], "action_test")

    def test_empty_retrieval_has_safe_response(self) -> None:
        routed = RoutedQuery("不存在的问题", [], Intent.SEMANTIC)
        result = Answerer.compose(routed.raw, routed, [])
        self.assertEqual(result["sources"], [])
        self.assertIn("没有检索到", result["answer"])


if __name__ == "__main__":
    unittest.main()
