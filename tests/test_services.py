from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.embedding.base import EmbeddingProvider
from src.index.bm25_store import BM25Index
from src.index.build_index import action_field_documents
from src.index.viewpoint_index import ViewpointIndex
from src.vectorstore.memory import InMemoryVectorStore


class FakeEmbedding(EmbeddingProvider):
    @property
    def name(self) -> str:
        return "fake"

    def embed_documents(self, texts, show_progress_bar=False):
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        return self._vector(text)

    @staticmethod
    def _vector(text):
        if "深蹲" in text:
            return [1.0, 0.0]
        return [0.0, 1.0]


class ServiceInterfaceTests(unittest.TestCase):
    def test_embedding_and_vector_store_are_replaceable(self) -> None:
        embeddings = FakeEmbedding()
        store = InMemoryVectorStore()
        store.add(
            ids=["squat", "bench"],
            documents=["深蹲动作", "卧推动作"],
            embeddings=embeddings.embed_documents(["深蹲动作", "卧推动作"]),
            metadatas=[{"kind": "action"}, {"kind": "action"}],
        )
        self.assertEqual(
            store.search(embeddings.embed_query("深蹲怎么练"), 1),
            ["squat"],
        )
        self.assertEqual(store.get_existing(["bench", "missing"]), ["bench"])

    def test_bm25_build_save_and_load(self) -> None:
        docs = [
            {"id": "a", "text": "深蹲 训练 股四头肌"},
            {"id": "b", "text": "卧推 训练 胸大肌"},
        ]
        index = BM25Index.build(docs)
        self.assertIn("深蹲", docs[0]["text"])
        self.assertEqual(len(index.search("深蹲", 1)), 1)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bm25.pkl"
            index.save(path)
            restored = BM25Index.load(path)
            self.assertEqual(len(restored.search("卧推", 1)), 1)

    def test_action_fields_are_linked_to_parent(self) -> None:
        actions = [
            {
                "id": "action_test",
                "name": "测试动作",
                "part": "腿部",
                "type": "复合动作",
                "target": ["股四头肌"],
                "assist": [],
                "cues": "控制下蹲",
                "errors": "膝盖内扣",
                "tips": "保持节奏",
            }
        ]
        documents = action_field_documents(actions)
        self.assertEqual(len(documents), 4)
        self.assertTrue(
            all(
                doc["meta"]["parent_id"] == "action_test"
                for doc in documents
            )
        )
        self.assertEqual(
            {doc["meta"]["field"] for doc in documents},
            {"errors", "cues", "tips", "targets"},
        )

    def test_action_viewpoint_index_is_persistent(self) -> None:
        viewpoints = [
            {
                "id": "viewpoint_1",
                "scope": "action",
                "action_id": "action_test",
                "speaker": "教练甲",
                "speaker_id": "coach_a",
                "title": "测试观点",
                "viewpoint": "保持动作稳定",
            }
        ]
        index = ViewpointIndex.build(viewpoints, {"action_test"})
        self.assertEqual(len(index.get("action_test")), 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "action_viewpoints.json"
            index.save(path)
            restored = ViewpointIndex.load(path)
            self.assertEqual(
                restored.get("action_test")[0]["speaker"], "教练甲"
            )


if __name__ == "__main__":
    unittest.main()
