from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.config import DB_DIR


REQUIRED_FILES = (
    "bm25.pkl",
    "bm25_fields.pkl",
    "chroma/chroma.sqlite3",
    "chroma_fields/chroma.sqlite3",
)
ARTIFACT_PATHS = (
    "bm25.pkl",
    "bm25_fields.pkl",
)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(path: str | Path) -> str:
    root = Path(path)
    digest = hashlib.sha256()
    for child in sorted(
        (
            item
            for item in root.rglob("*")
            if item.is_file()
            and not item.name.endswith(("-wal", "-shm", ".lock"))
            and item.name != "chroma.sqlite3"
        ),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        relative = child.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha256(child).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def build_artifact_hashes(db_dir: str | Path = DB_DIR) -> dict[str, str]:
    root = Path(db_dir)
    return {
        name: (
            tree_sha256(root / name)
            if (root / name).is_dir()
            else file_sha256(root / name)
        )
        for name in ARTIFACT_PATHS
    }


def check_index(db_dir: str | Path = DB_DIR) -> dict:
    root = Path(db_dir)
    manifest_path = root / "manifest.json"
    missing = [
        name
        for name in REQUIRED_FILES
        if not (root / name).is_file()
        or (root / name).stat().st_size == 0
    ]
    for name in ("chroma", "chroma_fields"):
        if not any((root / name).rglob("data_level0.bin")):
            missing.append(f"{name}/vector-data")
    if not manifest_path.is_file():
        missing.append("manifest.json")
        return {
            "status": "index_missing",
            "ready": False,
            "integrity": "missing",
            "missing": missing,
        }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "manifest_invalid",
            "ready": False,
            "integrity": "invalid",
            "missing": missing,
            "error": str(exc),
        }

    expected_artifacts = manifest.get("artifacts") or {}
    mismatched = []
    for name, expected in expected_artifacts.items():
        artifact = root / name
        if name not in ARTIFACT_PATHS or not artifact.exists():
            mismatched.append(name)
            continue
        actual = (
            tree_sha256(artifact)
            if artifact.is_dir()
            else file_sha256(artifact)
        )
        if actual != expected:
            mismatched.append(name)

    if missing:
        return {
            "status": "index_incomplete",
            "ready": False,
            "integrity": "invalid",
            "missing": missing,
            "mismatched": mismatched,
        }
    if not expected_artifacts:
        return {
            "status": "ok_unverified",
            "ready": True,
            "integrity": "unverified",
            "missing": [],
            "mismatched": [],
            "manifest": manifest,
        }
    if mismatched:
        return {
            "status": "index_corrupt",
            "ready": False,
            "integrity": "failed",
            "missing": [],
            "mismatched": mismatched,
            "manifest": manifest,
        }
    return {
        "status": "ok",
        "ready": True,
        "integrity": "verified",
        "missing": [],
        "mismatched": [],
        "manifest": manifest,
    }
