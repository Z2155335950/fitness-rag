from .pipeline import QueryPipeline

CASES = [
    ("深蹲怎么做", "action_detail"),
    ("平板杠铃卧推", "action_detail"),
    ("卧推", "action_detail"),
    ("杠铃深蹲", "action_detail"),
    ("怎么练上胸", "muscle_to_actions"),
    ("练胸的动作", "muscle_to_actions"),
    ("二头怎么练", "muscle_to_actions"),
    ("三角肌后束的动作", "muscle_to_actions"),
    ("臀怎么练", "muscle_to_actions"),
    ("没器械怎么练背", "muscle_to_actions"),
    ("家里没哑铃怎么练胸", "muscle_to_actions"),
    ("新手练腿的动作", "muscle_to_actions"),
    ("深蹲伤膝盖吗", "semantic"),
    ("深蹲和硬拉哪个好", "semantic"),
]


def main():
    pipe = QueryPipeline("data/parsed")
    passed = 0
    for q, expected in CASES:
        r = pipe.process(q)
        ok = r.intent.value == expected
        passed += ok
        mark = "✓" if ok else "✗"
        print(f"{mark} {q!r:28} → {r.intent.value:22} (期望 {expected})")
        for e in r.entities:
            preview = e.ids[:2] + (["..."] if len(e.ids) > 2 else [])
            print(f"      · [{e.type.value:12}] {e.text:10} → {e.canonical}  {preview}")
        if r.filters:
            print(f"      · filters: {r.filters}")
        print()
    print(f"==== 通过 {passed}/{len(CASES)} ====")


if __name__ == "__main__":
    main()