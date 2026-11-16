from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import PARSED_DIR
from src.index.build_index import _commit_staged_index, build
from src.index.health import build_artifact_hashes, check_index


def write_index_tree(root: Path, marker: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "bm25.pkl").write_bytes(f"bm25-{marker}".encode())
    (root / "bm25_fields.pkl").write_bytes(
        f"fields-{marker}".encode()
    )
    for name in ("chroma", "chroma_fields"):
        directory = root / name
        directory.mkdir()
        (directory / "chroma.sqlite3").write_bytes(
            f"sqlite-{marker}".encode()
        )
        (directory / "data_level0.bin").write_bytes(
            f"vectors-{marker}".encode()
        )


class IndexHealthTests(unittest.TestCase):
    def test_verified_manifest_detects_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_index_tree(root, "v1")
            manifest = {
                "documents": 2,
                "field_documents": 2,
                "artifacts": build_artifact_hashes(root),
            }
            (root / "manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            healthy = check_index(root)
            self.assertTrue(healthy["ready"])
            self.assertEqual(healthy["integrity"], "verified")

            (root / "bm25.pkl").write_bytes(b"corrupt")
            corrupt = check_index(root)
            self.assertFalse(corrupt["ready"])
            self.assertEqual(corrupt["status"], "index_corrupt")
            self.assertIn("bm25.pkl", corrupt["mismatched"])

    def test_atomic_failure_keeps_live_index_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "db"
            live.mkdir()
            sentinel = live / "chat_history.sqlite3"
            sentinel.write_bytes(b"history")

            with patch(
                "src.index.build_index.create_embedding_provider",
                side_effect=RuntimeError("model failed"),
            ):
                with self.assertRaises(RuntimeError):
                    build(
                        parsed_dir=PARSED_DIR,
                        db_dir=live,
                        atomic=True,
                    )

            self.assertEqual(sentinel.read_bytes(), b"history")
            self.assertFalse((live / "chroma").exists())
            self.assertEqual(
                list(root.glob(".db.staging-*")),
                [],
            )

    def test_commit_preserves_non_index_database_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live_db = root / "db"
            live_parsed = root / "parsed"
            staged_db = root / "staged" / "db"
            staged_parsed = root / "staged" / "parsed"
            write_index_tree(live_db, "old")
            write_index_tree(staged_db, "new")
            live_parsed.mkdir()
            staged_parsed.mkdir()
            (live_db / "chat_history.sqlite3").write_bytes(b"history")
            (live_parsed / "reverse_index.json").write_text(
                "old", encoding="utf-8"
            )
            (live_parsed / "action_viewpoints.json").write_text(
                "old", encoding="utf-8"
            )
            (staged_parsed / "reverse_index.json").write_text(
                "new", encoding="utf-8"
            )
            (staged_parsed / "action_viewpoints.json").write_text(
                "new", encoding="utf-8"
            )
            (staged_db / "manifest.json").write_text(
                "new-manifest", encoding="utf-8"
            )

            _commit_staged_index(
                staged_db,
                staged_parsed,
                live_db,
                live_parsed,
            )

            self.assertEqual(
                (live_db / "bm25.pkl").read_bytes(),
                b"bm25-new",
            )
            self.assertEqual(
                (live_db / "chat_history.sqlite3").read_bytes(),
                b"history",
            )
            self.assertEqual(
                (live_parsed / "reverse_index.json").read_text(
                    encoding="utf-8"
                ),
                "new",
            )


if __name__ == "__main__":
    unittest.main()
