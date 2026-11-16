from __future__ import annotations

import argparse
import json
import sys
from typing import TextIO

from src.rag import FitnessRAG


def configure_utf8(stream: TextIO) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="strict")


def main() -> None:
    configure_utf8(sys.stdout)
    configure_utf8(sys.stderr)
    parser = argparse.ArgumentParser(description="健美知识库 RAG 问答")
    parser.add_argument("query", help="自然语言问题")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    result = FitnessRAG().query(args.query, top_k=args.top_k)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["answer"])
        print(
            "\n来源："
            + "、".join(source["name"] for source in result["sources"])
        )


if __name__ == "__main__":
    main()
