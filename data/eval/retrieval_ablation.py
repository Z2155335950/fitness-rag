from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import EVAL_DIR, PARSED_DIR
from src.query.pipeline import QueryPipeline
from src.retrieval.channels import bm25_recall, vector
from src.retrieval.fusion import rrf
from src.retrieval.retriever import Retriever


def score(ids: list[str], expected: set[str], k: int = 5) -> dict:
    top = ids[:k]
    hits = [1 if doc_id in expected else 0 for doc_id in top]
    first_rank = next(
        (index + 1 for index, value in enumerate(hits) if value),
        None,
    )
    dcg = sum(
        value / math.log2(index + 2)
        for index, value in enumerate(hits)
    )
    ideal_hits = [1] * min(len(expected), k)
    idcg = sum(
        value / math.log2(index + 2)
        for index, value in enumerate(ideal_hits)
    )
    return {
        "hit": float(bool(first_rank)),
        "recall": len(set(top) & expected) / max(len(expected), 1),
        "mrr": 1.0 / first_rank if first_rank else 0.0,
        "ndcg": dcg / idcg if idcg else 0.0,
    }


def average(rows: list[dict]) -> dict[str, float]:
    keys = ("hit", "recall", "mrr", "ndcg")
    return {
        key: sum(row[key] for row in rows) / len(rows)
        for key in keys
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检索通道消融评测")
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
    questions = [
        item for item in questions if item.get("expect_any")
    ]

    pipeline = QueryPipeline(PARSED_DIR)
    retriever = Retriever(PARSED_DIR)
    methods = {
        "BM25": [],
        "Vector": [],
        "Hybrid RRF": [],
        "Full retrieval": [],
    }
    details = []

    for item in questions:
        expected = set(item["expect_any"])
        bm25_ids = bm25_recall(
            item["q"], retriever.bm25, k=args.top_k
        )
        vector_ids = vector(
            item["q"],
            retriever.embeddings,
            retriever.vector_store,
            k=args.top_k,
        )
        hybrid_ids = rrf([vector_ids, bm25_ids])[: args.top_k]
        routed = pipeline.process(item["q"])
        full_ids = [
            doc["id"]
            for doc in retriever.retrieve(routed, top_k=args.top_k)
        ]

        row = {"question": item["q"], "expected": sorted(expected)}
        for name, ids in (
            ("BM25", bm25_ids),
            ("Vector", vector_ids),
            ("Hybrid RRF", hybrid_ids),
            ("Full retrieval", full_ids),
        ):
            metrics = score(ids, expected, args.top_k)
            methods[name].append(metrics)
            row[name] = {**metrics, "ids": ids}
        details.append(row)

    summary = {
        name: average(rows) for name, rows in methods.items()
    }
    print(f"questions={len(questions)} k={args.top_k}")
    print(
        f"{'method':18} {'Hit':>7} {'Recall':>8} "
        f"{'MRR':>7} {'nDCG':>7}"
    )
    for name, metrics in summary.items():
        print(
            f"{name:18} {metrics['hit']:7.3f} "
            f"{metrics['recall']:8.3f} {metrics['mrr']:7.3f} "
            f"{metrics['ndcg']:7.3f}"
        )

    if args.write_report:
        output = EVAL_DIR / "retrieval_ablation_report.json"
        output.write_text(
            json.dumps(
                {"summary": summary, "details": details},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"report={output}")


if __name__ == "__main__":
    main()
