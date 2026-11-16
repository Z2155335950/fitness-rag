from __future__ import annotations

from collections import defaultdict

from src.chat.contracts import KnowledgeSnippet, TrainingProfile


class TrainingPlanBuilder:
    """Deterministic baseline used without an LLM and testable on its own."""

    TEMPLATES = {
        1: [["腿部", "胸部", "背部", "核心"]],
        2: [
            ["腿部", "胸部", "肩部", "核心"],
            ["背部", "后链", "手臂", "核心"],
        ],
        3: [
            ["腿部", "胸部", "肩部"],
            ["背部", "后链", "手臂"],
            ["腿部", "核心", "肩部"],
        ],
        4: [
            ["胸部", "肩部", "手臂"],
            ["腿部", "核心"],
            ["背部", "后链"],
            ["腿部", "胸部", "背部", "核心"],
        ],
    }

    @staticmethod
    def _sets_and_reps(profile: TrainingProfile) -> str:
        if profile.goal == "力量":
            return "3 组 × 4-6 次，组间休息 2-3 分钟"
        if profile.goal == "减脂":
            return "3 组 × 10-15 次，组间休息 60-90 秒"
        return "3 组 × 8-12 次，组间休息 90-120 秒"

    def build(
        self, profile: TrainingProfile, snippets: list[KnowledgeSnippet]
    ) -> str:
        actions = [
            snippet for snippet in snippets if snippet.kind == "action"
        ]
        citation_by_id = {
            snippet.id: index
            for index, snippet in enumerate(snippets, start=1)
        }
        unique: dict[str, KnowledgeSnippet] = {}
        for action in actions:
            unique.setdefault(action.name, action)
        pool = list(unique.values())
        if not pool:
            return "我现在没有找到足够可靠的动作资料，先不乱排计划。你有哪些器械？"

        days = max(1, min(profile.days_per_week or 3, 6))
        template = self.TEMPLATES.get(days)
        if template is None:
            template = [
                ["腿部", "胸部", "背部"],
                ["肩部", "手臂", "核心"],
                ["腿部", "后链"],
                ["胸部", "背部"],
                ["肩部", "手臂"],
                ["全身", "核心"],
            ][:days]

        by_part: dict[str, list[KnowledgeSnippet]] = defaultdict(list)
        for snippet in pool:
            by_part[snippet.part].append(snippet)

        used_names: set[str] = set()
        limit = 3 if (profile.session_minutes or 60) <= 30 else 5
        lines = [
            f"## {profile.experience or '新手'}·{profile.goal or '综合健身'}"
            f" {days} 天训练框架",
            "",
            f"器械：{'、'.join(profile.equipment) or '自重'}；"
            f"单次约 {profile.session_minutes or 60} 分钟；"
            f"组次：{self._sets_and_reps(profile)}。",
        ]

        for day_index, focus_parts in enumerate(template, start=1):
            selected: list[KnowledgeSnippet] = []
            for part in focus_parts:
                for snippet in by_part.get(part, []):
                    if snippet.name not in used_names:
                        selected.append(snippet)
                        used_names.add(snippet.name)
                        break
            for snippet in pool:
                if len(selected) >= limit:
                    break
                if snippet.name not in used_names:
                    selected.append(snippet)
                    used_names.add(snippet.name)
            # 小知识库可能没有足够多互不重复的动作。缺口用工位里
            # 尚未安排的动作补齐，优先重复基础动作也不排空训练日。
            selected_names = {item.name for item in selected}
            for snippet in pool:
                if len(selected) >= limit:
                    break
                if snippet.name not in selected_names:
                    selected.append(snippet)
                    selected_names.add(snippet.name)

            lines.extend([f"\n### 第 {day_index} 天", ""])
            if selected:
                lines.extend(
                    f"- {snippet.name} "
                    f"[{citation_by_id[snippet.id]}]："
                    f"{self._sets_and_reps(profile)}"
                    for snippet in selected[:limit]
                )
            else:
                lines.append("- 快走或低强度有氧 15-20 分钟")

        lines.extend(
            [
                "",
                "### 执行规则",
                "",
                "- 每次开始前热身 5-10 分钟，结束后做轻度放松。",
                "- 每组结束时保留约 2-3 次余力，动作稳定优先于加重量。",
                "- 连续两周都能完成且动作稳定后，每项动作只增加少量重量或次数。",
                "- 两次力量训练之间尽量间隔一天；睡眠不足或明显疲劳时主动降量。",
            ]
        )
        return "\n".join(lines)
