from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from src.config import (
    COLLECTION_NAME,
    DB_DIR,
    DEFAULT_MODEL,
    FIELD_COLLECTION_NAME,
    PARSED_DIR,
)
from src.embedding.factory import create_embedding_provider
from src.index.bm25_store import BM25Index
from src.index.health import build_artifact_hashes
from src.index.viewpoint_index import ViewpointIndex
from src.vectorstore.factory import create_vector_store


SUFFIXES = sorted(
    {
        "整体", "中下部", "中下束", "外侧头", "内侧头", "长头", "短头",
        "外侧", "内侧", "下部", "上部", "下沿", "宽度", "厚度", "深度",
        "中下", "前束", "后束", "中束", "上束", "下束",
    },
    key=len,
    reverse=True,
)

EXTRA_ALIASES = {
    "前束": "三角肌前束",
    "中束": "三角肌中束",
    "后束": "三角肌后束",
    "上斜方": "上斜方肌",
    "中斜方": "中斜方肌",
    "下斜方": "下斜方肌",
    "二头": "肱二头肌",
    "三头": "肱三头肌",
    "股四": "股四头肌",
    "腘绳": "腘绳肌",
    "上胸": "胸大肌上束",
    "中胸": "胸大肌中束",
    "下胸": "胸大肌下束",
    "胸肌": "胸大肌",
    "腹肌": "腹直肌",
    "背阔": "背阔肌",
    "斜方": "斜方肌",
    "臀": "臀大肌",
}

EQUIPMENT_ORDER = (
    "史密斯",
    "杠铃",
    "哑铃",
    "绳索",
    "T杠",
    "壶铃",
    "弹力带",
    "双杠",
    "单杠",
    "器械",
)

BODYWEIGHT_TERMS = (
    "俯卧撑",
    "引体",
    "悬垂",
    "卷腹",
    "平板支撑",
    "山羊挺身",
)


def load_jsonl(path: str | Path) -> list[dict]:
    path = Path(path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def infer_equipment(name: str) -> str:
    for term in EQUIPMENT_ORDER:
        if term in name:
            return term
    if any(term in name for term in BODYWEIGHT_TERMS):
        return "自重"
    return "其他"


def infer_difficulty(action: dict) -> str:
    name = action["name"]
    if any(
        term in name
        for term in ("高杠深蹲", "低杠深蹲", "传统硬拉", "引体", "双杠", "悬垂")
    ):
        return "高级"
    if action.get("type") in {"稳定动作", "孤立动作"}:
        return "初级"
    if any(term in name for term in ("腿举", "器械", "绳索", "蝴蝶机", "坐姿")):
        return "初级"
    return "中级"


def action_text(action: dict) -> str:
    return (
        f"动作：{action['name']}。部位：{action.get('part', '')}。"
        f"目标肌肉：{'、'.join(action.get('target', []))}。"
        f"辅助肌肉：{'、'.join(action.get('assist', []))}。"
        f"动作类型：{action.get('type', '')}。"
        f"发力要点：{action.get('cues', '')}。"
        f"常见错误：{action.get('errors', '')}。"
        f"训练提示：{action.get('tips', '')}。"
    )


FIELD_LABELS = {
    "errors": "常见错误",
    "cues": "发力要点",
    "tips": "训练提示",
    "targets": "目标肌群",
}


def action_field_documents(actions: list[dict]) -> list[dict]:
    documents = []
    for action in actions:
        values = {
            "errors": action.get("errors") or "",
            "cues": action.get("cues") or "",
            "tips": action.get("tips") or "",
            "targets": (
                f"目标：{'、'.join(action.get('target', []))}；"
                f"辅助：{'、'.join(action.get('assist', []))}"
            ),
        }
        for field, value in values.items():
            if not value.strip():
                continue
            label = FIELD_LABELS[field]
            documents.append(
                {
                    "id": f"{action['id']}::field::{field}",
                    "text": (
                        f"动作：{action['name']}。"
                        f"检索字段：{label}。内容：{value}。"
                    ),
                    "payload": action,
                    "meta": {
                        "id": f"{action['id']}::field::{field}",
                        "parent_id": action["id"],
                        "action_id": action["id"],
                        "action_name": action["name"],
                        "name": f"{action['name']}·{label}",
                        "kind": "action_field",
                        "field": field,
                        "part": action.get("part") or "",
                        "type": action.get("type") or "",
                        "equipment": infer_equipment(action["name"]),
                        "difficulty": infer_difficulty(action),
                    },
                }
            )
    return documents


def muscle_text(muscle: dict) -> str:
    aliases = "、".join(muscle.get("aliases") or [])
    return (
        f"肌肉：{muscle['name']}。别名：{aliases}。"
        f"所属部位：{muscle.get('group', '')}/{muscle.get('sub_group', '')}。"
        f"位置：{muscle.get('location', '')}。"
        f"功能：{muscle.get('function', '')}。"
        f"描述：{muscle.get('description', '')}。"
    )


def viewpoint_text(record: dict, action_name: str) -> str:
    return (
        "训练观点（这是个人观点，不等同于通用事实）。"
        f"关联动作：{action_name}。"
        f"观点人物：{record['speaker']}。"
        f"主题：{record['title']}。"
        f"来源：{record.get('platform', '')}"
        f" {record.get('source_url', '')} "
        f"链接状态：{record.get('source_status', '')}。"
        f"时间点：{record.get('timestamp', '')}。"
        f"观点内容：{record['viewpoint']}。"
        f"立场：{record.get('stance', '未标注')}。"
        f"备注：{record.get('note', '')}。"
    )


def _strip_suffixes(name: str) -> list[str]:
    out = [name]
    for suffix in SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            out.append(name[: -len(suffix)])
    return out


def build_reverse_index(
    actions: list[dict], muscles: list[dict], user_aliases: dict
) -> dict[str, list[str]]:
    name_to_id = {muscle["name"]: muscle["id"] for muscle in muscles}

    alias_to_ids: dict[str, set[str]] = defaultdict(set)
    for muscle in muscles:
        alias_to_ids[muscle["name"]].add(muscle["id"])
        for alias in muscle.get("aliases") or []:
            alias_to_ids[alias].add(muscle["id"])

    for alias, target in {**EXTRA_ALIASES, **user_aliases}.items():
        targets = [target] if isinstance(target, str) else list(target)
        for target_name in targets:
            for candidate in _strip_suffixes(str(target_name)):
                if candidate in name_to_id:
                    alias_to_ids[alias].add(name_to_id[candidate])
                    break

    # 部位词和肌群名都能映射到该肌群下的全部肌肉。
    for muscle in muscles:
        group = muscle.get("group") or ""
        sub_group = muscle.get("sub_group") or ""
        for group_name in (group, sub_group):
            if group_name:
                alias_to_ids[group_name].add(muscle["id"])
                alias_to_ids[group_name.removesuffix("肌群")].add(muscle["id"])

    known_terms = sorted(
        set(name_to_id) | set(alias_to_ids), key=len, reverse=True
    )

    def resolve(raw: str) -> set[str]:
        raw = raw.strip(" ，,、；;")
        candidates = _strip_suffixes(raw)
        for candidate in list(candidates):
            if candidate in alias_to_ids:
                candidates.extend(
                    token
                    for token in re.split(r"[、，,;；/\s]+", candidate)
                    if token
                )
        for candidate in sorted(set(candidates), key=len, reverse=True):
            if candidate in alias_to_ids:
                return set(alias_to_ids[candidate])

        # 原始字段常带方向词，如“胸大肌上束内侧”。最长实体包含
        # 匹配可以避免只命中更宽泛的“胸大肌”。
        for term in known_terms:
            if term in raw:
                return set(alias_to_ids[term])
        return set()

    direct: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    assist: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for order, action in enumerate(actions):
        target_count = max(len(action.get("target", [])), 1)
        for raw in action.get("target", []):
            for muscle_id in resolve(raw):
                direct[muscle_id].append(
                    (target_count, order, action["id"])
                )
        for raw in action.get("assist", []):
            for muscle_id in resolve(raw):
                assist[muscle_id].append(
                    (target_count, order, action["id"])
                )

    # 主动目标优先于辅助参与。例如问“二头怎么练”时，弯举应排在
    # 只是需要二头参与发力的引体向上和划船之前。
    reverse: dict[str, list[str]] = {}
    for muscle_id in set(direct) | set(assist):
        primary_candidates: dict[str, tuple[int, int]] = {}
        for target_count, order, action_id in direct.get(muscle_id, []):
            score = (target_count, order)
            if (
                action_id not in primary_candidates
                or score < primary_candidates[action_id]
            ):
                primary_candidates[action_id] = score
        primary = sorted(
            primary_candidates,
            key=lambda action_id: primary_candidates[action_id],
        )
        secondary = [
            action_id
            for _, _, action_id in sorted(assist.get(muscle_id, []))
            if action_id not in primary
        ]
        reverse[muscle_id] = list(dict.fromkeys(primary + secondary))
    return reverse


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _commit_staged_index(
    staged_db: Path,
    staged_derived: Path,
    db_dir: Path,
    parsed_dir: Path,
) -> None:
    db_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    backup_root = staged_db.parent / "backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    replacements = [
        (staged_db / "bm25.pkl", db_dir / "bm25.pkl"),
        (staged_db / "bm25_fields.pkl", db_dir / "bm25_fields.pkl"),
        (staged_db / "chroma", db_dir / "chroma"),
        (staged_db / "chroma_fields", db_dir / "chroma_fields"),
        (
            staged_derived / "reverse_index.json",
            parsed_dir / "reverse_index.json",
        ),
        (
            staged_derived / "action_viewpoints.json",
            parsed_dir / "action_viewpoints.json",
        ),
        (staged_db / "manifest.json", db_dir / "manifest.json"),
    ]
    committed: list[tuple[Path, Path | None]] = []
    try:
        for index, (source, target) in enumerate(replacements):
            backup = (
                backup_root / f"{index}-{target.name}"
                if target.exists()
                else None
            )
            if backup is not None:
                os.replace(target, backup)
            committed.append((target, backup))
            os.replace(source, target)
    except Exception:
        for target, backup in reversed(committed):
            _remove_path(target)
            if backup is not None:
                os.replace(backup, target)
        raise


def _build_atomically(
    model_name: str,
    parsed_dir: Path,
    db_dir: Path,
    local_files_only: bool,
) -> dict:
    staging_root = (
        db_dir.parent / f".{db_dir.name}.staging-{uuid.uuid4().hex}"
    )
    staged_db = staging_root / "db"
    staged_derived = staging_root / "parsed"
    staging_root.parent.mkdir(parents=True, exist_ok=True)
    staged_db.mkdir(parents=True, exist_ok=False)
    staged_derived.mkdir(parents=True, exist_ok=False)
    try:
        manifest = build(
            model_name=model_name,
            parsed_dir=parsed_dir,
            db_dir=staged_db,
            derived_dir=staged_derived,
            local_files_only=local_files_only,
            atomic=False,
        )
        _commit_staged_index(
            staged_db,
            staged_derived,
            db_dir,
            parsed_dir,
        )
        return manifest
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)


def build(
    model_name: str = DEFAULT_MODEL,
    parsed_dir: str | Path = PARSED_DIR,
    db_dir: str | Path = DB_DIR,
    derived_dir: str | Path | None = None,
    local_files_only: bool = False,
    atomic: bool = False,
) -> dict:
    parsed_dir = Path(parsed_dir)
    db_dir = Path(db_dir)
    derived_dir = Path(derived_dir) if derived_dir else parsed_dir
    if atomic:
        return _build_atomically(
            model_name,
            parsed_dir,
            db_dir,
            local_files_only,
        )
    actions = load_jsonl(parsed_dir / "actions.jsonl")
    muscles = load_jsonl(parsed_dir / "muscles.jsonl")
    viewpoint_paths = sorted(parsed_dir.glob("viewpoints*.jsonl"))
    viewpoints = []
    seen_viewpoint_ids: set[str] = set()
    for viewpoint_path in viewpoint_paths:
        for viewpoint in load_jsonl(viewpoint_path):
            if viewpoint["id"] not in seen_viewpoint_ids:
                seen_viewpoint_ids.add(viewpoint["id"])
                viewpoints.append(viewpoint)
    if not actions or not muscles:
        raise ValueError("解析数据为空，请先运行 parser")

    alias_path = parsed_dir / "muscle_aliases.json"
    user_aliases = (
        json.loads(alias_path.read_text(encoding="utf-8"))
        if alias_path.exists()
        else {}
    )

    docs: list[dict] = []
    action_by_id = {action["id"]: action for action in actions}
    for action in actions:
        docs.append(
            {
                "id": action["id"],
                "text": action_text(action),
                "payload": action,
                "meta": {
                    "id": action["id"],
                    "name": action["name"],
                    "kind": "action",
                    "part": action.get("part") or "",
                    "type": action.get("type") or "",
                    "target": "、".join(action.get("target", [])),
                    "assist": "、".join(action.get("assist", [])),
                    "equipment": infer_equipment(action["name"]),
                    "difficulty": infer_difficulty(action),
                },
            }
        )
    for muscle in muscles:
        docs.append(
            {
                "id": muscle["id"],
                "text": muscle_text(muscle),
                "payload": muscle,
                "meta": {
                    "id": muscle["id"],
                    "name": muscle["name"],
                    "kind": "muscle",
                    "part": muscle.get("group") or "",
                    "group": muscle.get("group") or "",
                    "sub_group": muscle.get("sub_group") or "",
                },
            }
        )
    for viewpoint in viewpoints:
        is_system = viewpoint.get("scope") == "system"
        action = action_by_id.get(viewpoint.get("action_id", ""))
        if not is_system and action is None:
            continue
        action_name = action["name"] if action else "训练体系（通用观点）"
        part = action.get("part") if action else "训练体系"
        docs.append(
            {
                "id": viewpoint["id"],
                "text": viewpoint_text(viewpoint, action_name),
                "payload": viewpoint,
                "meta": {
                    "id": viewpoint["id"],
                    "name": f"{viewpoint['speaker']}观点：{viewpoint['title']}",
                    "kind": "viewpoint",
                    "part": part or "",
                    "scope": viewpoint.get("scope") or "action",
                    "action_id": viewpoint.get("action_id") or "",
                    "action_name": action_name,
                    "speaker": viewpoint["speaker"],
                    "speaker_id": viewpoint["speaker_id"],
                    "source_type": viewpoint.get("source_type") or "",
                    "platform": viewpoint.get("platform") or "",
                    "source_url": viewpoint.get("source_url") or "",
                    "source_status": viewpoint.get("source_status") or "",
                    "timestamp": viewpoint.get("timestamp") or "",
                    "stance": viewpoint.get("stance") or "",
                    "category": viewpoint.get("category") or "",
                    "verified": bool(viewpoint.get("verified", False)),
                },
            }
        )
    field_docs = action_field_documents(actions)

    reverse = build_reverse_index(actions, muscles, user_aliases)
    derived_dir.mkdir(parents=True, exist_ok=True)
    (derived_dir / "reverse_index.json").write_text(
        json.dumps(reverse, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    viewpoint_index = ViewpointIndex.build(
        viewpoints, {action["id"] for action in actions}
    )
    viewpoint_index.save(derived_dir / "action_viewpoints.json")

    print(f"[..] 加载向量模型 {model_name}")
    embedding_provider = create_embedding_provider(
        model_name,
        local_files_only=local_files_only,
    )
    embeddings = embedding_provider.embed_documents(
        [doc["text"] for doc in docs],
        show_progress_bar=True,
    )
    field_embeddings = embedding_provider.embed_documents(
        [doc["text"] for doc in field_docs],
        show_progress_bar=True,
    )

    db_dir.mkdir(parents=True, exist_ok=True)
    vector_store = create_vector_store(
        db_dir / "chroma", COLLECTION_NAME
    )
    vector_store.reset()
    vector_store.add(
        ids=[doc["id"] for doc in docs],
        documents=[doc["text"] for doc in docs],
        metadatas=[doc["meta"] for doc in docs],
        embeddings=embeddings,
    )

    bm25 = BM25Index.build(docs)
    bm25.save(db_dir / "bm25.pkl")

    field_vector_store = create_vector_store(
        db_dir / "chroma_fields", FIELD_COLLECTION_NAME
    )
    field_vector_store.reset()
    field_vector_store.add(
        ids=[doc["id"] for doc in field_docs],
        documents=[doc["text"] for doc in field_docs],
        metadatas=[doc["meta"] for doc in field_docs],
        embeddings=field_embeddings,
    )
    field_bm25 = BM25Index.build(field_docs)
    field_bm25.save(db_dir / "bm25_fields.pkl")

    manifest = {
        "built_at": datetime.now().astimezone().isoformat(),
        "model": model_name,
        "documents": len(docs),
        "field_documents": len(field_docs),
        "total_documents": len(docs) + len(field_docs),
        "actions": len(actions),
        "muscles": len(muscles),
        "viewpoints": len(viewpoints),
        "viewpoint_files": [path.name for path in viewpoint_paths],
        "viewpoint_speakers": sorted(
            {viewpoint["speaker"] for viewpoint in viewpoints}
        ),
        "reverse_index_muscles": len(reverse),
        "action_viewpoint_links": viewpoint_index.count(),
        "artifacts": build_artifact_hashes(db_dir),
    }
    (db_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[ok] 建库完成：主文档 {len(docs)} 条，"
        f"字段辅助文档 {len(field_docs)} 条，"
        f"{len(reverse)} 个肌肉已关联动作"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="构建健美知识库索引")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="只使用本地模型缓存，不访问 Hugging Face",
    )
    parser.add_argument(
        "--no-atomic",
        action="store_true",
        help="直接写入现有索引，仅用于调试",
    )
    args = parser.parse_args()
    build(
        model_name=args.model,
        local_files_only=args.offline,
        atomic=not args.no_atomic,
    )


if __name__ == "__main__":
    main()
