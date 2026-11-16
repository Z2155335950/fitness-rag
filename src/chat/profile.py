from __future__ import annotations

import re

from src.chat.contracts import (
    ConversationIntent,
    ExtractedTurn,
    TrainingProfile,
)


CHINESE_NUMBERS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
}

GOALS = {
    "增肌": ("增肌", "长肌肉", "变壮", "肌肉量", "围度"),
    "减脂": ("减脂", "减肥", "瘦", "掉秤", "降体脂"),
    "力量": ("力量", "更强", "力量举", "三大项"),
    "塑形": ("塑形", "线条", "体态", "紧致"),
    "健康": ("健康", "体能", "心肺", "一般健身"),
}

EXPERIENCE = {
    "新手": ("新手", "小白", "刚开始", "零基础", "没练过"),
    "初级": ("初级", "入门", "练了几个月", "半年以内"),
    "中级": ("中级", "进阶", "一年", "两年", "有基础"),
    "高级": ("高级", "多年", "三年以上"),
}

EQUIPMENT = (
    "杠铃",
    "哑铃",
    "壶铃",
    "弹力带",
    "绳索",
    "器械",
    "单杠",
    "双杠",
    "史密斯",
)

GREETING_WORDS = {
    "你好",
    "您好",
    "嗨",
    "hi",
    "hello",
    "在吗",
    "早上好",
    "晚上好",
}

PLAN_WORDS = (
    "计划",
    "安排",
    "方案",
    "训练频率",
    "推荐训练",
    "排一份",
    "排个",
)

KNOWLEDGE_WORDS = (
    "动作",
    "怎么练",
    "如何练",
    "推荐几个",
    "观点",
    "看法",
    "怎么看待",
    "容量",
    "减载",
    "deload",
    "训练体系",
    "库里",
    "知识库",
    "有没有",
    "是否收录",
    "谁认为",
    "谁持有",
    "谁提出",
    "怎么做",
    "发力",
    "错误",
    "技巧",
    "肌肉",
    "练哪里",
    "替代",
)

NEGATED_EQUIPMENT_PREFIXES = (
    "没有",
    "没",
    "无",
    "不用",
    "不需要",
    "不带",
    "不方便用",
    "排除",
)
BODYWEIGHT_WORDS = ("无器械", "没有器械", "没器械", "徒手", "自重")
BODY_PARTS = (
    "膝",
    "肩",
    "腰",
    "腿",
    "脚",
    "手",
    "肘",
    "腕",
    "踝",
    "背",
    "胸",
    "关节",
    "肌肉",
)


class ProfileExtractor:
    """Rule-based slot extraction, independent from the conversational model."""

    @staticmethod
    def _number(value: str) -> int | None:
        if value.isdigit():
            return int(value)
        return CHINESE_NUMBERS.get(value)

    def _extract_days(self, text: str) -> int | None:
        patterns = (
            r"每周\s*(?:练)?\s*([1-7一二两三四五六七])\s*(?:天|次|练)",
            r"(?:一周|每星期)\s*(?:练)?\s*([1-7一二两三四五六七])\s*(?:天|次|练)",
            r"([1-7一二两三四五六七])\s*(?:天|次)\s*(?:一|每)周",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._number(match.group(1))
        return None

    def _extract_minutes(self, text: str) -> int | None:
        if "半小时" in text:
            return 30
        if "一小时" in text or "1小时" in text:
            return 60
        match = re.search(r"(\d{2,3})\s*分钟", text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _is_negated_equipment(text: str, start: int) -> bool:
        prefix = text[max(0, start - 6) : start]
        return prefix.endswith(NEGATED_EQUIPMENT_PREFIXES)

    def _equipment(
        self, text: str
    ) -> tuple[list[str], list[str]]:
        available: list[str] = []
        excluded: list[str] = []
        lower = text.lower()
        for item in EQUIPMENT:
            start = lower.find(item.lower())
            while start != -1:
                target = (
                    excluded
                    if self._is_negated_equipment(text, start)
                    else available
                )
                target.append(item)
                start = lower.find(item.lower(), start + len(item))

        available = list(dict.fromkeys(available))
        excluded = list(dict.fromkeys(excluded))
        available = [item for item in available if item not in excluded]

        bodyweight_only = any(word in text for word in BODYWEIGHT_WORDS)
        if bodyweight_only and not available:
            available = ["自重"]
        return available, excluded

    @staticmethod
    def _has_safety_signal(text: str) -> bool:
        without_negated_issues = re.sub(
            r"(?:没有|没|无|不)(?:明显|太|特别)?"
            r"(?:疼痛|疼|痛|受伤|麻木|发麻|肿胀)",
            "",
            text,
        )
        if any(
            word in without_negated_issues
            for word in (
                "受伤",
                "扭伤",
                "拉伤",
                "骨折",
                "肿胀",
                "麻木",
                "发麻",
                "刺痛",
                "康复",
                "关节不稳",
                "关节不舒服",
                "医生",
            )
        ):
            return True
        if (
            "疼" in without_negated_issues
            or "痛" in without_negated_issues
        ) and "痛快" not in without_negated_issues:
            return True

        body = "|".join(BODY_PARTS)
        patterns = (
            rf"(?:{body}).{{0,6}}(?:不舒服|难受|卡住|发紧|不稳)",
            rf"(?:伤|损伤)(?:到|了)?(?:{body})",
            rf"(?:{body}).{{0,6}}(?:伤|损伤)",
            rf"(?:{body}).{{0,3}}麻",
        )
        return any(
            re.search(pattern, without_negated_issues)
            for pattern in patterns
        )

    def extract(self, text: str) -> ExtractedTurn:
        normalized = text.strip()
        lower = normalized.lower()
        update = TrainingProfile()

        for label, words in GOALS.items():
            if any(word in normalized for word in words):
                update.goal = label
                break
        for label, words in EXPERIENCE.items():
            if any(word in normalized for word in words):
                update.experience = label
                break

        update.days_per_week = self._extract_days(normalized)
        update.session_minutes = self._extract_minutes(normalized)
        (
            update.equipment,
            update.equipment_excluded,
        ) = self._equipment(normalized)
        update.plan_requested = any(word in normalized for word in PLAN_WORDS)

        safety_flag = self._has_safety_signal(normalized)
        if safety_flag:
            update.limitations.append(normalized)

        has_profile_update = any(
            (
                update.goal,
                update.experience,
                update.days_per_week,
                update.session_minutes,
                update.equipment,
            )
        )

        if safety_flag:
            intent = ConversationIntent.SAFETY
        elif normalized.rstrip("。！!?？ ") in GREETING_WORDS or lower in GREETING_WORDS:
            intent = ConversationIntent.GREETING
        else:
            knowledge_hint = any(
                word in normalized
                for word in (
                    "观点",
                    "看法",
                    "谁认为",
                    "谁持有",
                    "谁提出",
                    "知识库",
                    "库里",
                    "是否收录",
                )
            )
            if update.plan_requested and not knowledge_hint:
                intent = ConversationIntent.PLAN
            elif any(word in normalized for word in KNOWLEDGE_WORDS):
                intent = ConversationIntent.KNOWLEDGE
            elif (
                update.days_per_week
                and any(word in normalized for word in ("怎么练", "如何练"))
            ):
                intent = ConversationIntent.PLAN
            elif has_profile_update:
                intent = ConversationIntent.PROFILE_UPDATE
            else:
                intent = ConversationIntent.SMALL_TALK

        return ExtractedTurn(
            intent=intent,
            profile_update=update,
            should_retrieve=intent
            in {
                ConversationIntent.KNOWLEDGE,
                ConversationIntent.PLAN,
                ConversationIntent.SAFETY,
            },
            safety_flag=safety_flag,
        )
