from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class EntityType(str, Enum):
    MUSCLE = "muscle"
    MUSCLE_GROUP = "muscle_group"
    ACTION = "action"
    ACTION_GROUP = "action_group"
    EQUIPMENT = "equipment"
    DIFFICULTY = "difficulty"


@dataclass
class Entity:
    text: str
    start: int
    end: int
    canonical: str
    ids: list[str] = field(default_factory=list)
    type: EntityType = EntityType.MUSCLE
    confidence: float = 1.0


class Intent(str, Enum):
    ACTION_DETAIL = "action_detail"
    MUSCLE_TO_ACTIONS = "muscle_to_actions"
    FILTER = "filter"
    SEMANTIC = "semantic"


@dataclass
class RoutedQuery:
    raw: str
    entities: list[Entity]
    intent: Intent
    filters: dict = field(default_factory=dict)
    debug: dict = field(default_factory=dict)