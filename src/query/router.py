from __future__ import annotations
from .schema import Entity, EntityType, Intent

TRAIN_WORDS = ["怎么练", "练什么", "如何练", "有什么动作", "动作有哪些",
               "训练", "锻炼", "练", "动作", "刺激", "激活"]
DETAIL_WORDS = ["怎么做", "如何做", "动作要点", "要点", "注意事项",
                "常见错误", "发力", "教程", "标准", "技巧", "姿势"]
SEMANTIC_HINT_WORDS = ["伤", "疼", "痛", "康复", "危害", "好处", "效果",
                       "原理", "为什么", "科学", "研究", "区别", "对比",
                       "哪个好", "哪个更", "vs", "还是", "会不会",
                       "圆肩", "体态"]
NEG_PREFIX = ("没", "无", "没有", "不用", "不需要")
NEG_EQUIPMENT_SET = {"无器械", "没有器械", "没器械", "无器材",
                     "徒手", "自重", "居家", "家里"}
ALL_EQUIPMENT = {"杠铃", "哑铃", "绳索", "器械", "T杠", "壶铃",
                 "弹力带", "单杠", "双杠", "史密斯"}
FIELD_WORDS = {
    "errors": ("常见错误", "错误", "做错", "代偿", "避免", "风险", "容易"),
    "cues": ("发力要点", "动作要点", "怎么做", "如何做", "姿势", "技巧", "技术"),
    "tips": ("训练提示", "节奏", "组数", "次数", "建议", "安排"),
    "targets": ("目标肌群", "练哪里", "刺激哪里", "主要练", "练什么"),
}


def extract_filters(query: str, entities: list[Entity]) -> dict:
    filters: dict = {}
    eq_inc, eq_exc = [], []
    equipment_entities = [
        entity
        for entity in entities
        if entity.type == EntityType.EQUIPMENT
    ]
    explicit_equipment = set()
    for entity in equipment_entities:
        if entity.text in NEG_EQUIPMENT_SET:
            continue
        prefix = query[max(0, entity.start - 3):entity.start]
        if not any(prefix.endswith(word) for word in NEG_PREFIX):
            explicit_equipment.add(entity.text)

    for e in equipment_entities:
        if e.text in NEG_EQUIPMENT_SET:
            # “家里有哑铃”中的“家里”是场景，不是“无器械”。
            # 只有没有明确正向器械时，居家/家里才作为无器械条件。
            if e.text in {"家里", "居家"} and explicit_equipment:
                continue
            eq_exc.append(e.text)
            continue
        prefix = query[max(0, e.start - 3):e.start]
        if any(prefix.endswith(n) for n in NEG_PREFIX):
            eq_exc.append(e.text)
        else:
            eq_inc.append(e.text)
    if eq_inc:
        filters["equipment_include"] = eq_inc
    if eq_exc:
        if any(word in NEG_EQUIPMENT_SET for word in eq_exc):
            # “徒手/居家/没器械”要求排除常见器械，而不是把否定词当成
            # 一个器材名称去匹配动作元数据。
            filters["equipment_exclude"] = sorted(ALL_EQUIPMENT)
            filters["prefer_bodyweight"] = True
        else:
            filters["equipment_exclude"] = eq_exc

    diff = [e.canonical for e in entities if e.type == EntityType.DIFFICULTY]
    if diff:
        filters["difficulty"] = diff

    parts = [e.canonical for e in entities if e.type == EntityType.MUSCLE_GROUP]
    if parts:
        filters["body_parts"] = parts

    fields = [
        field
        for field, words in FIELD_WORDS.items()
        if any(word in query for word in words)
    ]
    if fields:
        filters["fields"] = fields
    return filters


def route(query: str, entities: list[Entity]) -> tuple[Intent, dict]:
    filters = extract_filters(query, entities)

    actions = [e for e in entities if e.type == EntityType.ACTION]
    action_groups = [e for e in entities if e.type == EntityType.ACTION_GROUP]
    muscles = [e for e in entities
               if e.type in (EntityType.MUSCLE, EntityType.MUSCLE_GROUP)]

    has_train = any(w in query for w in TRAIN_WORDS)
    has_semantic = any(w in query for w in SEMANTIC_HINT_WORDS)

    if actions:
        return Intent.ACTION_DETAIL, filters
    if action_groups and not has_semantic:
        return Intent.ACTION_DETAIL, filters
    if muscles and has_train and not has_semantic:
        return Intent.MUSCLE_TO_ACTIONS, filters
    if filters and not has_semantic:
        return Intent.FILTER, filters
    return Intent.SEMANTIC, filters
