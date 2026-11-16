from __future__ import annotations

from src.chat.contracts import ConversationIntent, KnowledgeSnippet, TrainingProfile
from src.chat.plan import TrainingPlanBuilder


class FallbackResponder:
    """Conversation-capable local response path when no model is configured."""

    def __init__(self, plan_builder: TrainingPlanBuilder | None = None):
        self.plan_builder = plan_builder or TrainingPlanBuilder()

    @staticmethod
    def _profile_summary(profile: TrainingProfile) -> str:
        facts = []
        if profile.goal:
            facts.append(f"目标是{profile.goal}")
        if profile.experience:
            facts.append(f"目前按{profile.experience}安排")
        if profile.days_per_week:
            facts.append(f"每周 {profile.days_per_week} 天")
        if profile.equipment:
            facts.append(f"可用{'、'.join(profile.equipment)}")
        return "，".join(facts)

    def _ask_missing(self, profile: TrainingProfile) -> str:
        missing = profile.missing_plan_fields()
        prompts = {
            "训练目标": "你更想增肌、减脂，还是提升力量？",
            "每周训练天数": "你每周能安排几天训练？",
            "可用器械": "你是在家里还是健身房，能用哪些器械？",
        }
        questions = [prompts[item] for item in missing[:2]]
        prefix = self._profile_summary(profile)
        if prefix:
            prefix += "。"
        return prefix + "为了让计划真正适合你，我还想确认：" + " ".join(questions)

    @staticmethod
    def _knowledge_answer(
        snippets: list[KnowledgeSnippet],
    ) -> str:
        indexed = list(enumerate(snippets, start=1))
        actions = [
            (index, item)
            for index, item in indexed
            if item.kind == "action"
        ]
        muscles = [
            (index, item)
            for index, item in indexed
            if item.kind == "muscle"
        ]
        viewpoints = [
            (index, item)
            for index, item in indexed
            if item.kind == "viewpoint"
        ]
        if actions:
            selected = actions[:3]
            lines = ["我查到这些相关动作，你可以先看最匹配的一个："]
            for index, item in selected:
                content = item.content
                cue = content.split("要点：", 1)[-1].split("。", 1)[0]
                lines.append(
                    f"- **{item.name}** [{index}]："
                    f"{cue or '知识库暂未提供动作要点'}"
                )
            if viewpoints:
                lines.append("")
                lines.append("相关人物观点：")
                for index, item in viewpoints[:5]:
                    lines.append(f"- [{index}] {item.content}")
            return "\n".join(lines)
        if viewpoints:
            return "\n".join(
                f"- [{index}] {item.content}"
                for index, item in viewpoints[:2]
            )
        if muscles:
            return "\n".join(
                f"- **{item.name}** [{index}]：{item.content}"
                for index, item in muscles[:2]
            )
        return "这个知识库暂时没有足够具体的资料。你可以补充动作名或想练的部位。"

    def respond(
        self,
        message: str,
        profile: TrainingProfile,
        intent: ConversationIntent,
        snippets: list[KnowledgeSnippet],
        safety_flag: bool,
    ) -> str:
        if safety_flag:
            return (
                "先别硬扛着练。你能具体说说是哪一侧、什么动作会痛，"
                "以及是刺痛还是酸胀吗？如果伴随肿胀、麻木或关节不稳，"
                "先停止诱发动作并找医生或康复师评估。"
            )
        if intent == ConversationIntent.GREETING:
            return (
                "你好，我在。你可以直接说自己的训练目标、当前水平、"
                "每周能练几天和手头器械，我会陪你把计划理顺。"
            )
        if intent == ConversationIntent.PLAN:
            if profile.missing_plan_fields():
                return self._ask_missing(profile)
            return self.plan_builder.build(profile, snippets)
        if intent == ConversationIntent.KNOWLEDGE:
            return self._knowledge_answer(snippets)
        if intent == ConversationIntent.PROFILE_UPDATE:
            summary = self._profile_summary(profile)
            if profile.missing_plan_fields():
                return f"记下了：{summary}。\n\n" + self._ask_missing(profile)
            return (
                f"记下了：{summary}。信息已经足够，"
                "你可以直接说“给我排一份计划”。"
            )
        return (
            "可以，我们慢慢聊。你想先解决训练计划、某个动作怎么做，"
            "还是最近的训练安排哪里不顺？"
        )
