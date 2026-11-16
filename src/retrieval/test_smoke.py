from src.query.pipeline import QueryPipeline
from .retriever import Retriever


def main():
    pipe = QueryPipeline("data/parsed")
    retr = Retriever("data/parsed", "db")

    cases = [
        ("深蹲怎么做", 5),
        ("怎么练上胸", 5),
        ("练胸的动作", 5),
        ("二头怎么练", 5),
        ("臀怎么练", 5),
        ("没器械怎么练背", 5),
        ("深蹲伤膝盖吗", 5),
    ]

    for q, k in cases:
        rq = pipe.process(q)
        docs = retr.retrieve(rq, top_k=k)
        print(f"\nQ: {q}   intent={rq.intent.value}")
        for d in docs:
            m = d["meta"]
            print(f"   · {d['id']:30}  [{m.get('kind','?'):6}] {m.get('name','')}")


if __name__ == "__main__":
    main()