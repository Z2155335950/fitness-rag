from __future__ import annotations

import re

from src.chat.contracts import (
    ConversationIntent,
    KnowledgeSnippet,
    TrainingProfile,
)


CITATION_PATTERN = re.compile(r"\[(\d+)\]")
NO_EVIDENCE_ANSWER = (
    "当前文档没有足够的相关依据，我不能据此给出具体训练事实。"
    "请补充动作名、训练部位，或提供包含该内容的文档。"
)


def requires_grounding(
    intent: ConversationIntent,
    profile: TrainingProfile,
) -> bool:
    if intent == ConversationIntent.KNOWLEDGE:
        return True
    return (
        intent == ConversationIntent.PLAN
        and not profile.missing_plan_fields()
    )


def citation_refs(answer: str) -> list[int]:
    refs: list[int] = []
    for raw in CITATION_PATTERN.findall(answer):
        ref = int(raw)
        if ref not in refs:
            refs.append(ref)
    return refs


def validate_grounded_answer(
    answer: str,
    snippets: list[KnowledgeSnippet],
) -> tuple[bool, list[int]]:
    if not snippets:
        return False, []
    refs = citation_refs(answer)
    if not refs:
        return False, []
    if any(ref < 1 or ref > len(snippets) for ref in refs):
        return False, []
    return True, refs


def cited_sources(
    refs: list[int],
    snippets: list[KnowledgeSnippet],
) -> list[dict[str, str]]:
    sources = []
    for ref in refs:
        data = snippets[ref - 1].to_dict()
        data["citation"] = f"[{ref}]"
        sources.append(data)
    return sources


def cited_records(
    refs: list[int],
    snippets: list[KnowledgeSnippet],
) -> list[dict[str, str | int]]:
    return [
        {
            "ref": ref,
            "id": snippets[ref - 1].id,
            "name": snippets[ref - 1].name,
        }
        for ref in refs
    ]
