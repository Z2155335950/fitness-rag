from __future__ import annotations
import re
from pathlib import Path

from .common import clean_heading, write_jsonl
from src.config import PROJECT_ROOT

MUSCLES_MD = PROJECT_ROOT / "data/raw/健美-人体肌肉名称库.md"
OUT = PROJECT_ROOT / "data/parsed/muscles.jsonl"


def _new_muscle(body: str, group: str | None, sub_group: str | None,
                raw_line: str) -> dict:
    """body 形如 '胸大肌：分为胸大肌上束、...' / '三角肌前束：肩前侧，...' / '髂腰肌'"""
    name, desc = body, ""
    if "：" in body or ":" in body:
        name, desc = re.split(r"[：:]", body, 1)
        name, desc = name.strip(), desc.strip()

    aliases: list[str] = []

    # 1) 名字末尾带括号 → 括号里当别名（在顿号处理之前，避免误切）
    m = re.match(r"^(.+?)[（(](.+?)[）)]\s*$", name)
    if m:
        name = m.group(1).strip()
        aliases.extend(split_paren := [x.strip() for x in
                        re.split(r"[、，,]", m.group(2)) if x.strip()])
        _ = split_paren

    # 2) 名字里顿号分隔的多个肌肉（如 '腹外斜肌、腹内斜肌'）
    parts = [x.strip() for x in re.split(r"[、，,]", name) if x.strip()]
    if len(parts) > 1:
        aliases.extend(parts[1:])
        name = parts[0]

    # 3) desc 里带 '分为' → 拆子束
    children: list[dict] = []
    if "分为" in desc:
        sub = desc.split("分为", 1)[1]
        for it in re.split(r"[、，,]", sub):
            it = re.sub(r"[（(].*?[）)]", "", it.strip()).strip()
            if it:
                children.append({"name": it, "desc": "", "raw": raw_line})

    return {
        "id": "muscle_" + name,
        "name": name,
        "group": group,
        "sub_group": sub_group,
        "aliases": aliases,
        "location": "",
        "function": "",
        "description": desc if "分为" not in desc else "",
        "children": children,
        "raw": raw_line,
    }


def parse(md_path: str = MUSCLES_MD) -> list[dict]:
    lines = Path(md_path).read_text(encoding="utf-8").splitlines()
    muscles: list[dict] = []
    group = sub_group = None
    current: dict | None = None

    def flush():
        nonlocal current
        if current is None:
            return
        children = current.pop("children", [])
        seen = {current["name"]}
        muscles.append(current)
        for c in children:
            if c["name"] in seen:
                continue
            seen.add(c["name"])
            muscles.append({
                "id": "muscle_" + c["name"],
                "name": c["name"],
                "group": current["group"],
                "sub_group": current["sub_group"],
                "parent": current["name"],
                "aliases": [c["name"]],
                "location": c.get("desc", ""),
                "function": "",
                "description": "",
                "raw": c.get("raw", ""),
            })
        current = None

    for raw in lines:
        line = raw.rstrip()
        if not line or line.startswith(">"):
            continue
        if line.startswith("### "):
            flush()
            sub_group = clean_heading(line[4:])
            continue
        if line.startswith("## "):
            flush()
            group = clean_heading(line[3:])
            sub_group = None
            continue
        if line.startswith("# "):
            continue

        # 编号条目：'1. xxx' '2. xxx'
        m = re.match(r"^\s*(\d+)\.\s*(.+)$", line)
        if m:
            flush()
            current = _new_muscle(m.group(2).strip(), group, sub_group, line)
            continue
        if current is None:
            continue

        # 子列表项：'- 上斜方肌：颈侧到肩峰...'
        mb = re.match(r"^\s*[-*]\s*(.+?)[：:](.+)$", line)
        if mb:
            current["children"].append({
                "name": mb.group(1).strip(),
                "desc": mb.group(2).strip(),
                "raw": line,
            })
            continue

        # 字段行：位置 / 功能
        hit = False
        for key, prefix in (("location", "位置"), ("function", "功能")):
            if line.startswith(prefix + "：") or line.startswith(prefix + ":"):
                current[key] = re.split(r"[：:]", line, 1)[1].strip()
                hit = True
                break
        if hit:
            continue

        # 其他当描述续行
        current["description"] = (current.get("description", "") + " " + line).strip()

    flush()
    return muscles


if __name__ == "__main__":
    rows = parse()
    write_jsonl(OUT, rows)
