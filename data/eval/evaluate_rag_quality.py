from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chat.api import get_orchestrator
from src.chat.providers import create_chat_model
from src.config import EVAL_DIR


DIRECT_SYSTEM = """
你是一名经验丰富的健身教练。请直接回答用户问题，表达自然、准确。
如果信息不足以确认，请明确说不知道。不要声称访问过任何本地知识库。
""".strip()

JUDGE_SYSTEM = """
你是严格的 RAG 答案评测员。只输出一个 JSON 对象，不要输出解释或 Markdown。
比较两个匿名回答，判断回答是否准确、是否拒答不存在的库内信息、是否存在无依据
或与参考答案矛盾的声明。只统计与用户问题直接相关的事实声明；寒暄和“以下是
回答”等废话不计入。若核心事实错误，correct=false。若问题涉及当前知识库是否
收录某项内容，而回答凭空声称收录或给出不存在的细节，则必须记为 unsupported
或 contradicted。若回答正确说明知识库未收录，列举知识库中确实存在的相关动作
不算幻觉。对于错误前提或不存在的观点，明确纠正前提并说明没有该推荐，应判为
correct=true、abstained=true。JSON 格式：
{
  "A": {
    "correct": true,
    "abstained": false,
    "total_claims": 3,
    "unsupported_claims": 0,
    "contradicted_claims": 0
  },
  "B": {
    "correct": true,
    "abstained": false,
    "total_claims": 3,
    "unsupported_claims": 0,
    "contradicted_claims": 0
  }
}
""".strip()


def parse_json_object(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("评测模型没有返回 JSON")
    return json.loads(text[start : end + 1])


def bootstrap_ci(
    values: list[float],
    seed: int = 42,
    rounds: int = 2000,
) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    means = []
    for _ in range(rounds):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    return means[int(rounds * 0.025)], means[int(rounds * 0.975)]


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 与无 RAG 生成质量试点")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--ids", default="", help="逗号分隔的题目 ID")
    args = parser.parse_args()

    questions = [
        json.loads(line)
        for line in (EVAL_DIR / "rag_quality_pilot.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if args.limit:
        questions = questions[: args.limit]
    selected_ids = {
        item.strip() for item in args.ids.split(",") if item.strip()
    }
    if selected_ids:
        questions = [
            item for item in questions if item["id"] in selected_ids
        ]

    model = create_chat_model()
    if not model.available:
        raise RuntimeError("对话模型未配置")
    rag = get_orchestrator()
    if not rag.model.available:
        raise RuntimeError("RAG 对话模型未配置")

    output_path = EVAL_DIR / "rag_quality_pilot_results.json"
    existing = []
    if args.resume and output_path.exists():
        existing = json.loads(
            output_path.read_text(encoding="utf-8")
        ).get("rows", [])
    completed = {row["id"] for row in existing}
    rows = list(existing)
    if selected_ids:
        rows = [row for row in rows if row["id"] not in selected_ids]

    for index, item in enumerate(questions, start=1):
        if item["id"] in completed and item["id"] not in selected_ids:
            continue
        print(
            f"[{index}/{len(questions)}] {item['id']} {item['q']}",
            flush=True,
        )
        direct = model.complete(
            [
                {"role": "system", "content": DIRECT_SYSTEM},
                {"role": "user", "content": item["q"]},
            ]
        )
        rag_reply = rag.chat(item["q"], session_id=None)

        rng = random.Random(f"judge:{item['id']}")
        rag_is_a = rng.choice([True, False])
        answer_a = rag_reply.answer if rag_is_a else direct
        answer_b = direct if rag_is_a else rag_reply.answer
        judge_prompt = (
            f"问题：{item['q']}\n"
            f"是否应从当前本地知识库回答："
            f"{'是' if item['answerable'] else '否，库中没有可靠信息'}\n"
            f"参考答案：{item['reference']}\n\n"
            f"回答 A：\n{answer_a}\n\n"
            f"回答 B：\n{answer_b}"
        )
        judged = parse_json_object(
            model.complete(
                [
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": judge_prompt},
                ]
            )
        )
        rag_judgement = judged["A" if rag_is_a else "B"]
        direct_judgement = judged["B" if rag_is_a else "A"]
        row = {
            "id": item["id"],
            "category": item["category"],
            "question": item["q"],
            "answerable": item["answerable"],
            "reference": item["reference"],
            "direct_answer": direct,
            "rag_answer": rag_reply.answer,
            "rag_sources": [
                {
                    "name": source["name"],
                    "kind": source["kind"],
                }
                for source in rag_reply.sources
            ],
            "judge_order": "RAG=A" if rag_is_a else "RAG=B",
            "direct": direct_judgement,
            "rag": rag_judgement,
        }
        rows.append(row)
        output_path.write_text(
            json.dumps(
                {"rows": rows},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"  direct correct={direct_judgement['correct']} "
            f"rag correct={rag_judgement['correct']}",
            flush=True,
        )

    def rate(row: dict, method: str) -> float:
        result = row[method]
        claims = max(int(result.get("total_claims", 0)), 1)
        bad = int(result.get("unsupported_claims", 0)) + int(
            result.get("contradicted_claims", 0)
        )
        return bad / claims

    answerable = [row for row in rows if row["answerable"]]
    unanswerable = [row for row in rows if not row["answerable"]]
    direct_accuracy = sum(
        bool(row["direct"]["correct"]) for row in rows
    ) / len(rows)
    rag_accuracy = sum(
        bool(row["rag"]["correct"]) for row in rows
    ) / len(rows)
    direct_hallucination = sum(
        rate(row, "direct") for row in rows
    ) / len(rows)
    rag_hallucination = sum(rate(row, "rag") for row in rows) / len(rows)
    direct_abstention = (
        sum(bool(row["direct"]["abstained"]) for row in unanswerable)
        / len(unanswerable)
        if unanswerable
        else 0.0
    )
    rag_abstention = (
        sum(bool(row["rag"]["abstained"]) for row in unanswerable)
        / len(unanswerable)
        if unanswerable
        else 0.0
    )

    accuracy_diffs = [
        float(bool(row["rag"]["correct"]))
        - float(bool(row["direct"]["correct"]))
        for row in rows
    ]
    hallucination_diffs = [
        rate(row, "direct") - rate(row, "rag") for row in rows
    ]
    acc_ci = bootstrap_ci(accuracy_diffs)
    hall_ci = bootstrap_ci(hallucination_diffs)
    summary = {
        "questions": len(rows),
        "answerable_questions": len(answerable),
        "unanswerable_questions": len(unanswerable),
        "direct_accuracy": direct_accuracy,
        "rag_accuracy": rag_accuracy,
        "accuracy_lift": rag_accuracy - direct_accuracy,
        "accuracy_lift_ci95": acc_ci,
        "direct_hallucination_rate": direct_hallucination,
        "rag_hallucination_rate": rag_hallucination,
        "hallucination_reduction": (
            direct_hallucination - rag_hallucination
        ),
        "hallucination_reduction_ci95": hall_ci,
        "direct_unanswerable_abstention": direct_abstention,
        "rag_unanswerable_abstention": rag_abstention,
        "rag_source_coverage": sum(
            bool(row["rag_sources"]) for row in rows
        )
        / len(rows),
    }
    report = {"summary": summary, "rows": rows}
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("\n=== PILOT SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"report={output_path}")


if __name__ == "__main__":
    main()
