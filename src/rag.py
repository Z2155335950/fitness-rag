from __future__ import annotations

from pathlib import Path

from src.config import DB_DIR, DEFAULT_MODEL, PARSED_DIR
from src.index.viewpoint_index import ViewpointIndex
from src.query.pipeline import QueryPipeline
from src.query.schema import EntityType, Intent, RoutedQuery
from src.retrieval.retriever import Retriever


SAFETY_WORDS = ("伤", "疼", "痛", "康复", "矫正", "治疗")


def _join(values: list[str] | None, empty: str = "未注明") -> str:
    return "、".join(values or []) or empty


class Answerer:
    """Deterministic answer composer grounded in retrieved knowledge rows."""

    @staticmethod
    def _action_detail(action: dict) -> str:
        lines = [
            f"### {action['name']}",
            "",
            f"- 目标肌群：{_join(action.get('target'))}",
            f"- 辅助肌群：{_join(action.get('assist'))}",
            f"- 动作类型：{action.get('type') or '未注明'}",
            f"- 发力要点：{action.get('cues') or '知识库暂未提供。'}",
        ]
        if action.get("errors"):
            lines.append(f"- 常见错误：{action['errors']}")
        if action.get("tips"):
            lines.append(f"- 训练提示：{action['tips']}")
        return "\n".join(lines)

    @staticmethod
    def _muscle_detail(muscle: dict) -> str:
        group = "/".join(
            part
            for part in (muscle.get("group"), muscle.get("sub_group"))
            if part
        )
        lines = [
            f"### {muscle['name']}",
            "",
            f"- 所属部位：{group or '未注明'}",
            f"- 位置：{muscle.get('location') or '知识库暂未提供。'}",
            f"- 主要功能：{muscle.get('function') or '知识库暂未提供。'}",
        ]
        return "\n".join(lines)

    @classmethod
    def compose(
        cls, query: str, routed: RoutedQuery, docs: list[dict]
    ) -> dict:
        if not docs:
            return {
                "answer": "知识库中没有检索到足够相关的内容。可以换一种动作名、肌肉名或训练条件再问。",
                "sources": [],
            }

        actions = [
            doc for doc in docs if doc.get("meta", {}).get("kind") == "action"
        ]
        muscles = [
            doc for doc in docs if doc.get("meta", {}).get("kind") == "muscle"
        ]
        parts: list[str] = []

        if routed.intent == Intent.ACTION_DETAIL and actions:
            primary_action = actions[0]
            parts.append(cls._action_detail(primary_action.get("payload", {})))
            viewpoints = [
                doc
                for doc in docs
                if doc.get("meta", {}).get("kind") == "viewpoint"
                and doc.get("meta", {}).get("action_id")
                == primary_action.get("id")
            ]
            if viewpoints:
                view_lines = ["**观点补充**", ""]
                for doc in viewpoints[:5]:
                    viewpoint = doc.get("payload", {})
                    where = viewpoint.get("title", "")
                    timestamp = viewpoint.get("timestamp", "")
                    if timestamp:
                        where += f" · {timestamp}"
                    source_url = viewpoint.get("source_url", "")
                    source_status = viewpoint.get("source_status", "")
                    if source_status not in {"linked", "partial"}:
                        source_url = ""
                    label = (
                        "视频级来源，时间点待核"
                        if source_status == "partial"
                        else "原视频"
                    )
                    source_suffix = (
                        f"（[{label}]({source_url})）" if source_url else ""
                    )
                    view_lines.append(
                        f"- **{viewpoint.get('speaker', '')}**"
                        f"（{where}）：{viewpoint.get('viewpoint', '')}"
                        f"{source_suffix}"
                    )
                view_lines.append(
                    "\n> 以上是个人训练观点，不等同于所有训练者都必须采用的标准。"
                )
                parts.append("\n".join(view_lines))
            related = [
                doc["meta"]["name"]
                for doc in docs
                if doc.get("meta", {}).get("kind") == "action"
            ][1:4]
            if related:
                parts.append(
                    "**相关知识库动作：** " + "、".join(related)
                )
        elif routed.intent == Intent.MUSCLE_TO_ACTIONS and actions:
            parts.append(f"## {query} 的训练动作")
            parts.append("")
            for index, doc in enumerate(actions, start=1):
                payload = doc.get("payload", {})
                cue = payload.get("cues") or "知识库暂未提供动作要点。"
                parts.append(
                    f"{index}. **{payload.get('name', doc['id'])}**  "
                    f"目标：{_join(payload.get('target'))}  \n"
                    f"   {cue}"
                )
        elif routed.intent in {Intent.SEMANTIC, Intent.FILTER}:
            parts.append("## 检索到的相关依据")
            for index, doc in enumerate(docs[:5], start=1):
                payload = doc.get("payload", {})
                meta = doc.get("meta", {})
                label = payload.get("name", doc["id"])
                if meta.get("kind") == "action":
                    evidence = (
                        f"目标：{_join(payload.get('target'))}；"
                        f"要点：{payload.get('cues') or '知识库暂未提供。'}"
                    )
                elif meta.get("kind") == "viewpoint":
                    evidence = (
                        f"{payload.get('speaker', '')} 的训练观点："
                        f"{payload.get('viewpoint', '')}"
                    )
                else:
                    evidence = (
                        f"位置：{payload.get('location') or '未注明'}；"
                        f"功能：{payload.get('function') or '未注明'}"
                    )
                parts.append(f"{index}. **{label}**：{evidence}")
        elif muscles:
            parts.append(cls._muscle_detail(muscles[0].get("payload", {})))
        else:
            parts.append("## 检索到的相关内容")
            for index, doc in enumerate(docs[:5], start=1):
                payload = doc.get("payload", {})
                label = payload.get("name", doc["id"])
                field = payload.get("cues") or payload.get("function") or ""
                parts.append(f"{index}. **{label}**：{field}".rstrip())

        if any(word in query for word in SAFETY_WORDS):
            parts.append(
                "\n> 知识库主要提供训练动作信息，不能替代医学诊断。"
                "如果疼痛持续、伴随肿胀或关节不稳，请先停止相关动作并咨询医生或康复师。"
            )

        sources = []
        for doc in docs:
            meta = doc.get("meta", {})
            sources.append(
                {
                    "id": doc["id"],
                    "name": meta.get("name", doc["id"]),
                    "kind": meta.get("kind", ""),
                    "part": meta.get("part", ""),
                    "equipment": meta.get("equipment", ""),
                    "difficulty": meta.get("difficulty", ""),
                    "speaker": meta.get("speaker", ""),
                    "action_id": meta.get("action_id", ""),
                    "source_url": meta.get("source_url", ""),
                    "source_status": meta.get("source_status", ""),
                    "timestamp": meta.get("timestamp", ""),
                }
            )
        return {"answer": "\n\n".join(parts), "sources": sources}


class FitnessRAG:
    def __init__(
        self,
        parsed_dir: str | Path = PARSED_DIR,
        db_dir: str | Path = DB_DIR,
        model_name: str = DEFAULT_MODEL,
    ):
        self.pipeline = QueryPipeline(parsed_dir)
        self.retriever = Retriever(parsed_dir, db_dir, model_name)
        self.viewpoint_index = ViewpointIndex.load(
            Path(parsed_dir) / "action_viewpoints.json"
        )

    def query(self, query: str, top_k: int = 5) -> dict:
        query = query.strip()
        if not query:
            raise ValueError("问题不能为空")
        routed = self.pipeline.process(query)
        docs = self.retriever.retrieve(routed, top_k=top_k)
        result = Answerer.compose(query, routed, docs)
        result.update(
            {
                "query": query,
                "intent": routed.intent.value,
                "entities": [
                    {
                        "text": entity.text,
                        "canonical": entity.canonical,
                        "type": entity.type.value,
                    }
                    for entity in routed.entities
                ],
                "filters": routed.filters,
            }
        )
        if routed.intent == Intent.ACTION_DETAIL:
            primary_action = next(
                (
                    doc
                    for doc in docs
                    if doc.get("meta", {}).get("kind") == "action"
                ),
                None,
            )
            if primary_action is not None:
                action = primary_action.get("payload", {})
                related_viewpoints = self.viewpoint_index.get(
                    primary_action["id"]
                )
                result["action_detail"] = {
                    "id": primary_action["id"],
                    "name": action.get("name", ""),
                    "part": action.get("part", ""),
                    "target": action.get("target", []),
                    "assist": action.get("assist", []),
                    "type": action.get("type", ""),
                    "cues": action.get("cues", ""),
                    "errors": action.get("errors", ""),
                    "tips": action.get("tips", ""),
                    "related_viewpoints": related_viewpoints,
                    "viewpoint_count": len(related_viewpoints),
                }
        return result

    def action_viewpoints(self, action_id: str) -> list[dict]:
        return self.viewpoint_index.get(action_id)
