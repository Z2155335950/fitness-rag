from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ConversationIntent(str, Enum):
    GREETING = "greeting"
    SMALL_TALK = "small_talk"
    PROFILE_UPDATE = "profile_update"
    KNOWLEDGE = "knowledge"
    PLAN = "plan"
    SAFETY = "safety"


@dataclass
class TrainingProfile:
    goal: str | None = None
    experience: str | None = None
    days_per_week: int | None = None
    equipment: list[str] = field(default_factory=list)
    equipment_excluded: list[str] = field(default_factory=list)
    session_minutes: int | None = None
    limitations: list[str] = field(default_factory=list)
    plan_requested: bool = False

    def merge(self, update: "TrainingProfile") -> None:
        for field_name in (
            "goal",
            "experience",
            "days_per_week",
            "session_minutes",
        ):
            value = getattr(update, field_name)
            if value is not None:
                setattr(self, field_name, value)
        if update.equipment:
            self.equipment = list(dict.fromkeys(update.equipment))
            self.equipment_excluded = [
                item
                for item in self.equipment_excluded
                if item not in self.equipment
            ]
        if update.equipment_excluded:
            self.equipment_excluded = list(
                dict.fromkeys(
                    self.equipment_excluded + update.equipment_excluded
                )
            )
            self.equipment = [
                item
                for item in self.equipment
                if item not in self.equipment_excluded
            ]
        if update.limitations:
            self.limitations = list(
                dict.fromkeys(self.limitations + update.limitations)
            )
        self.plan_requested = self.plan_requested or update.plan_requested

    def missing_plan_fields(self) -> list[str]:
        missing = []
        if not self.goal:
            missing.append("训练目标")
        if not self.days_per_week:
            missing.append("每周训练天数")
        if not self.equipment:
            missing.append("可用器械")
        return missing

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedTurn:
    intent: ConversationIntent
    profile_update: TrainingProfile = field(default_factory=TrainingProfile)
    should_retrieve: bool = False
    safety_flag: bool = False


@dataclass(frozen=True)
class KnowledgeSnippet:
    id: str
    name: str
    kind: str
    part: str
    content: str
    speaker: str = ""
    source_url: str = ""
    source_status: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class KnowledgeSearchResult:
    snippets: list[KnowledgeSnippet] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatReply:
    answer: str
    session_id: str
    mode: str
    intent: str
    request_id: str = ""
    answer_id: int | None = None
    sources: list[dict[str, str]] = field(default_factory=list)
    citations: list[dict[str, str | int]] = field(default_factory=list)
    profile: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
