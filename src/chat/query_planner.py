from __future__ import annotations

from dataclasses import dataclass

from src.chat.contracts import ConversationIntent, TrainingProfile


@dataclass(frozen=True)
class PlannedQuery:
    text: str
    purpose: str
    k: int = 2


class TrainingQueryPlanner:
    """Builds intent-specific query variants before retrieval."""

    BODY_PARTS = ("腿部", "胸部", "背部", "肩部", "手臂", "核心")

    @staticmethod
    def _profile_text(profile: TrainingProfile) -> str:
        values = [
            profile.goal or "",
            profile.experience or "",
            "、".join(profile.equipment),
            " ".join(
                f"没有{item}" for item in profile.equipment_excluded
            ),
        ]
        return " ".join(value for value in values if value)

    def plan(
        self,
        message: str,
        profile: TrainingProfile,
        intent: ConversationIntent,
        top_k: int = 6,
    ) -> list[PlannedQuery]:
        profile_text = self._profile_text(profile)
        if intent != ConversationIntent.PLAN:
            return [
                PlannedQuery(
                    text=f"{message} {profile_text}".strip(),
                    purpose="direct",
                    k=top_k,
                )
            ]

        per_part = max(2, min(3, top_k // 2))
        queries = [
            PlannedQuery(
                text=f"{part} {profile_text} 训练动作",
                purpose=f"body_part:{part}",
                k=per_part,
            )
            for part in self.BODY_PARTS
        ]

        queries.append(
            PlannedQuery(
                text=(
                    f"{profile_text} 复合动作 自由重量 "
                    "训练动作 力量 增肌"
                ).strip(),
                purpose="compound",
                k=2,
            )
        )

        if profile.goal == "减脂":
            style = "全身 复合动作 循环 训练"
        elif profile.goal == "力量":
            style = "复合动作 深蹲 卧推 硬拉 训练"
        elif profile.experience == "新手":
            style = "新手 稳定动作 基础动作 训练"
        else:
            style = "孤立动作 肌肉刺激 训练"
        queries.append(
            PlannedQuery(
                text=f"{profile_text} {style}".strip(),
                purpose="training_style",
                k=2,
            )
        )

        queries.append(
            PlannedQuery(
                text=f"{profile_text} 核心 稳定动作 核心训练".strip(),
                purpose="core_stability",
                k=1,
            )
        )
        return queries
