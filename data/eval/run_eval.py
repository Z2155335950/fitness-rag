from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import EVAL_DIR, PARSED_DIR
from src.query.pipeline import QueryPipeline
from src.retrieval.retriever import Retriever


def main() -> None:
    parser = argparse.ArgumentParser(description="运行健美 RAG 检索评测")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    questions = [
        json.loads(line)
        for line in (EVAL_DIR / "questions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    pipe = QueryPipeline(PARSED_DIR)
    retriever = Retriever(PARSED_DIR)

    hit = 0
    total = 0
    intent_ok = 0
    report = []

    for question in questions:
        routed = pipe.process(question["q"])
        intent_match = routed.intent.value == question["intent"]
        intent_ok += intent_match

        docs = retriever.retrieve(routed, top_k=args.top_k)
        got = [doc["id"] for doc in docs]
        expected = set(question.get("expect_any", []))
        if expected:
            total += 1
            is_hit = bool(expected & set(got))
            hit += is_hit
            mark = "PASS" if is_hit else "MISS"
        else:
            is_hit = None
            mark = "----"
        intent_mark = "PASS" if intent_match else "MISS"
        print(
            f"{mark:4} intent={intent_mark:4} "
            f"{question['q']:24} -> {got[:3]}"
        )
        report.append(
            {
                "question": question["q"],
                "expected_intent": question["intent"],
                "actual_intent": routed.intent.value,
                "intent_match": intent_match,
                "expected_ids": sorted(expected),
                "retrieved_ids": got,
                "hit": is_hit,
            }
        )

    summary = {
        f"hit@{args.top_k}": f"{hit}/{total}",
        "intent_accuracy": f"{intent_ok}/{len(questions)}",
        "categories": report,
    }
    print(
        f"\n==== hit@{args.top_k}: {hit}/{total}  "
        f"意图准确率: {intent_ok}/{len(questions)} ===="
    )
    if args.write_report:
        output = EVAL_DIR / "latest_report.json"
        output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"报告已写入 {output}")


if __name__ == "__main__":
    main()
