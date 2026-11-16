from __future__ import annotations

import json
from pathlib import Path


class ViewpointIndex:
    """Persistent action_id -> structured viewpoint references."""

    def __init__(self, mapping: dict[str, list[dict]]):
        self.mapping = mapping

    @classmethod
    def build(
        cls,
        viewpoints: list[dict],
        action_ids: set[str],
    ) -> "ViewpointIndex":
        mapping: dict[str, list[dict]] = {}
        for viewpoint in viewpoints:
            action_id = viewpoint.get("action_id") or ""
            scope = viewpoint.get("scope") or (
                "action" if action_id else "system"
            )
            if (
                scope != "action"
                or action_id not in action_ids
            ):
                continue
            mapping.setdefault(action_id, []).append(
                {
                    "id": viewpoint["id"],
                    "speaker": viewpoint["speaker"],
                    "speaker_id": viewpoint["speaker_id"],
                    "title": viewpoint["title"],
                    "platform": viewpoint.get("platform") or "",
                    "source_url": viewpoint.get("source_url") or "",
                    "source_status": viewpoint.get(
                        "source_status", ""
                    ),
                    "timestamp": viewpoint.get("timestamp") or "",
                    "viewpoint": viewpoint["viewpoint"],
                    "category": viewpoint.get("category") or "",
                    "stance": viewpoint.get("stance") or "",
                    "verified": bool(viewpoint.get("verified", False)),
                }
            )
        for items in mapping.values():
            items.sort(
                key=lambda item: (
                    item["speaker"],
                    item["timestamp"],
                    item["title"],
                )
            )
        return cls(mapping)

    @classmethod
    def load(cls, path: str | Path) -> "ViewpointIndex":
        path = Path(path)
        if not path.exists():
            return cls({})
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.mapping, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, action_id: str) -> list[dict]:
        return list(self.mapping.get(action_id, []))

    def count(self) -> int:
        return sum(len(items) for items in self.mapping.values())
