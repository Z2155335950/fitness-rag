from __future__ import annotations
import json
from collections import Counter
from pathlib import Path


def peek(path: str, n: int = 3):
    rows = [json.loads(l) for l in Path(path).read_text("utf-8").splitlines() if l.strip()]
    print(f"\n== {path}  共 {len(rows)} 条 ==")
    for r in rows[:n]:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    return rows


if __name__ == "__main__":
    actions = peek("data/parsed/actions.jsonl")
    print("\n按部位统计动作：", dict(Counter(a["part"] for a in actions)))
    print("动作类型：", dict(Counter(a["type"] for a in actions)))
    print("缺 cues 的动作：", [a["name"] for a in actions if not a["cues"]][:10])

    muscles = peek("data/parsed/muscles.jsonl")
    print("\n按 group 统计肌肉：", dict(Counter(m["group"] for m in muscles)))
    print("有 parent 的子束：",
          [(m["name"], m["parent"]) for m in muscles if m.get("parent")][:10])