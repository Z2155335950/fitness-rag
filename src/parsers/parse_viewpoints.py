from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.config import PARSED_DIR


DEFAULT_OUTPUT = PARSED_DIR / "viewpoints.jsonl"
DEFAULT_ACTIONS = PARSED_DIR / "actions.jsonl"

ACTION_ID_ALIASES = {
    "action_杠铃俯身划船": "action_杠铃俯身划船（正手）",
    "action_农夫行走": "action_杠铃农夫行走",
    "action_锤式弯举": "action_锤式弯举（哑铃）",
    "action_前锯肌绳索前推": "action_前锯肌绳索前推（Serratus Punch）",
    "action_直杆绳索下压": "action_绳索下压（直杆）",
    "action_山羊挺身": "action_山羊挺身（背伸）",
    "action_凯索耸肩": "action_凯索耸肩（Kelso Shrug）",
    "action_北欧挺": "action_北欧挺（北欧离心）",
    "action_反向腕弯举": "action_反向腕弯举（掌心向下）",
    "action_安德森深蹲": "action_安德森深蹲（安全架底位启动深蹲）",
    "action_哑铃平板卧推": "action_平板哑铃卧推",
}

ACTION_ID_EXPANSIONS = {
    "action_腿弯举": [
        "action_俯卧腿弯举",
        "action_坐姿腿弯举",
    ],
    "action_罗马尼亚硬拉": ["action_罗马尼亚硬拉（杠铃）"],
    "action_山羊挺身": ["action_山羊挺身（背伸）"],
}


def _json_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value.replace('\\"', '"').replace("\\n", "\n")


def _field(block: str, name: str) -> str | None:
    match = re.search(
        rf'^\s*"{re.escape(name)}"\s*:\s*"((?:\\.|[^"\\])*)"',
        block,
        re.MULTILINE,
    )
    return _json_string(match.group(1)) if match else None


def _bool_field(block: str, name: str) -> bool:
    match = re.search(
        rf'^\s*"{re.escape(name)}"\s*:\s*(true|false)',
        block,
        re.MULTILINE | re.IGNORECASE,
    )
    return bool(match and match.group(1).lower() == "true")


def _object_blocks(text: str) -> list[str]:
    starts = [match.start() for match in re.finditer(r"(?m)^\s*\{\s*$", text)]
    blocks = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        blocks.append(text[start:end].strip())
    return blocks


def _parse_object(block: str) -> dict[str, Any] | None:
    try:
        value = json.loads(block.rstrip().removesuffix(","))
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass

    # The source file has one object whose speaker_id/title fields are
    # corrupt. Extract valid fields independently and let normalization fill
    # safe defaults for the two missing fields.
    result: dict[str, Any] = {}
    for name in (
        "action_id",
        "speaker",
        "speaker_id",
        "source_type",
        "title",
        "platform",
        "source_url",
        "timestamp",
        "viewpoint",
        "category",
        "stance",
        "note",
    ):
        value = _field(block, name)
        if value is not None:
            result[name] = value
    if "verified" in block:
        result["verified"] = _bool_field(block, "verified")
    return result or None


def load_source(path: str | Path) -> tuple[list[dict[str, Any]], list[str]]:
    text = Path(path).read_text(encoding="utf-8")
    errors: list[str] = []
    records: list[dict[str, Any]] = []

    # Also accept a normal JSON array or one-object-per-line JSONL.
    try:
        value = json.loads(text)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)], errors
        if isinstance(value, dict):
            return [value], errors
    except json.JSONDecodeError:
        pass

    line_records = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            errors.append(
                f"第 {line_number} 行: JSON 不完整或格式错误，已跳过"
            )
            continue
        if isinstance(item, dict):
            line_records.append(item)
    if line_records:
        return line_records, errors

    for index, block in enumerate(_object_blocks(text), start=1):
        item = _parse_object(block)
        if item:
            records.append(item)
        else:
            errors.append(f"对象 {index}: 无法提取任何有效字段")
    return records, errors


def normalize(
    records: list[dict[str, Any]],
    action_ids: set[str],
    action_name_to_id: dict[str, str] | None = None,
    action_aliases: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], Counter]:
    output = []
    seen = set()
    stats = Counter()
    action_name_to_id = action_name_to_id or {}
    action_aliases = action_aliases or {}

    for record in records:
        raw_action_id = str(record.get("action_id") or "").strip()
        exercise_name = str(record.get("exercise_name") or "").strip()
        resolved_exercise_name = action_aliases.get(
            exercise_name, exercise_name
        )
        mapped_exercise_id = action_name_to_id.get(resolved_exercise_name)

        if mapped_exercise_id:
            target_action_ids = [mapped_exercise_id]
            stats["resolved_exercise_name"] += 1
        elif raw_action_id in ACTION_ID_ALIASES:
            target_action_ids = [ACTION_ID_ALIASES[raw_action_id]]
            stats["remapped_action"] += 1
        elif raw_action_id in ACTION_ID_EXPANSIONS:
            target_action_ids = ACTION_ID_EXPANSIONS[raw_action_id]
            stats["expanded_action"] += 1
        else:
            target_action_ids = [raw_action_id]

        speaker = str(record.get("speaker") or "").strip()
        viewpoint = str(record.get("viewpoint") or "").strip()
        category = str(record.get("category") or "动作观点").strip()
        is_system = (
            raw_action_id.startswith("action_训练体系_")
            or (not raw_action_id and category == "训练体系")
            or (
                raw_action_id.startswith("action_general_")
                and category == "训练体系"
                and not mapped_exercise_id
            )
        )
        if (not raw_action_id and not is_system) or not speaker or not viewpoint:
            stats["missing_required"] += 1
            continue
        if not is_system and any(
            action_id not in action_ids
            for action_id in target_action_ids
        ):
            stats["unknown_action"] += 1
            continue

        speaker_id = str(record.get("speaker_id") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", speaker_id):
            speaker_id = (
                "speaker_"
                + hashlib.sha1(speaker.encode("utf-8")).hexdigest()[:8]
            )
            stats["repaired_speaker_id"] += 1

        title = str(record.get("title") or "").strip() or viewpoint[:36]
        timestamp = str(record.get("timestamp") or "").strip()
        targets = [""] if is_system else target_action_ids
        for action_id in targets:
            signature = (
                action_id or raw_action_id,
                speaker_id,
                timestamp,
                viewpoint,
            )
            if signature in seen:
                stats["duplicates"] += 1
                continue
            seen.add(signature)

            result = {
                "id": "viewpoint_"
                + hashlib.sha1(
                    "|".join(signature).encode("utf-8")
                ).hexdigest()[:16],
                "scope": "system" if is_system else "action",
                "action_id": action_id,
                "topic_id": raw_action_id if is_system else "",
                "speaker": speaker,
                "speaker_id": speaker_id,
                "source_type": str(record.get("source_type") or "video"),
                "title": title,
                "platform": str(record.get("platform") or ""),
                "source_url": str(record.get("source_url") or ""),
                "timestamp": timestamp,
                "viewpoint": viewpoint,
                "category": category,
                "stance": str(record.get("stance") or "未标注"),
                "verified": bool(record.get("verified", False)),
                "note": str(record.get("note") or ""),
            }
            parsed_url = urlparse(result["source_url"])
            generic_hosts = {
                "...",
                "douyin.com",
                "www.douyin.com",
                "bilibili.com",
                "www.bilibili.com",
                "youtube.com",
                "www.youtube.com",
            }
            has_specific_path = parsed_url.path not in {"", "/"}
            result["source_status"] = (
                "linked"
                if parsed_url.scheme in {"http", "https"}
                and parsed_url.netloc.lower() not in generic_hosts
                or (
                    parsed_url.netloc.lower()
                    in {"douyin.com", "www.douyin.com",
                        "bilibili.com", "www.bilibili.com",
                        "youtube.com", "www.youtube.com"}
                    and has_specific_path
                )
                else "needs_source_link"
            )
            output.append(result)
            stats["written"] += 1
            if is_system:
                stats["system_viewpoints"] += 1
    return output, stats


def convert(
    source: str | Path,
    output: str | Path = DEFAULT_OUTPUT,
    actions: str | Path = DEFAULT_ACTIONS,
) -> dict[str, int]:
    action_rows = [
        json.loads(line)
        for line in Path(actions).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    action_ids = {row["id"] for row in action_rows}
    action_name_to_id = {row["name"]: row["id"] for row in action_rows}
    aliases_path = Path(actions).with_name("action_aliases.json")
    action_aliases = (
        json.loads(aliases_path.read_text(encoding="utf-8"))
        if aliases_path.exists()
        else {}
    )
    records, errors = load_source(source)
    normalized, stats = normalize(
        records, action_ids, action_name_to_id, action_aliases
    )

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in normalized:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    stats["parsed_blocks"] = len(records)
    stats["parse_errors"] = len(errors)
    print(
        f"[ok] {output}: {len(normalized)} 条观点，"
        f"解析块 {len(records)}，解析错误 {len(errors)}"
    )
    for key, value in sorted(stats.items()):
        print(f"  {key}: {value}")
    if errors:
        print("[warn] 解析错误：")
        for error in errors:
            print(f"  - {error}")
    return dict(stats)


def main() -> None:
    parser = argparse.ArgumentParser(description="转换训练观点 JSONL")
    parser.add_argument("source", help="原始观点文件")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--actions", default=str(DEFAULT_ACTIONS))
    args = parser.parse_args()
    convert(args.source, args.output, args.actions)


if __name__ == "__main__":
    main()
