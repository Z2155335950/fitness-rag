from __future__ import annotations
import json
import re
from pathlib import Path


def clean_heading(s: str) -> str:
    """去掉标题里的括号备注，如 '腿部肌群（健美最大肌群）' → '腿部肌群'"""
    return re.sub(r"[（(].*?[）)]", "", s).strip()


def split_list(s: str) -> list[str]:
    """按 、，,;； 切分，去空"""
    if not s:
        return []
    return [p.strip() for p in re.split(r"[、，,;；]", s) if p.strip()]


def write_jsonl(path: str | Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[write] {path}  ({len(rows)} rows)")