from __future__ import annotations
import re
from pathlib import Path

from .common import clean_heading, split_list, write_jsonl
from src.config import PROJECT_ROOT

ACTIONS_MD = PROJECT_ROOT / "data/raw/健美-训练动作库.md"
OUT = PROJECT_ROOT / "data/parsed/actions.jsonl"

ACTION_TYPES = {"复合动作", "孤立动作", "拉伸动作", "稳定动作",
                "复合稳定动作", "离心孤立动作"}

FIELD_PREFIXES = (("cues", "发力要点"), ("errors", "常见错误"), ("tips", "训练提示"))


def _parse_header(header: str) -> tuple[str, str, str]:
    """'目标：胸大肌整体｜辅助：三角肌前束、肱三头肌｜复合动作' → (target, assist, type)"""
    target = assist = type_ = ""
    for seg in re.split(r"[｜|]", header):
        seg = seg.strip()
        if not seg:
            continue
        if re.match(r"^(目标|目标肌群)\s*[：:]", seg):
            target = re.split(r"[：:]", seg, 1)[1].strip()
        elif re.match(r"^(辅助|辅助肌群)\s*[：:]", seg):
            assist = re.split(r"[：:]", seg, 1)[1].strip()
        elif seg in ("辅助", "辅助肌群"):
            assist = ""
        elif seg in ACTION_TYPES or seg.endswith("动作"):
            type_ = seg
        else:
            type_ = type_ or seg           # 兜底：不认识的段当类型
    if assist in ("无", "无。", "-", "—"):
        assist = ""
    return target, assist, type_


def parse(md_path: str = ACTIONS_MD) -> list[dict]:
    lines = Path(md_path).read_text(encoding="utf-8").splitlines()
    actions: list[dict] = []
    current_part: str | None = None
    current: dict | None = None

    def flush():
        nonlocal current
        if current is not None:
            actions.append(current)
            current = None

    for raw in lines:
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("## "):
            flush()
            current_part = clean_heading(line[3:])
            continue
        m = re.match(r"^【(.+?)】\s*[｜|](.+)$", line)
        if m:
            flush()
            name = m.group(1).strip()
            target, assist, type_ = _parse_header(m.group(2))
            current = {
                "id": "action_" + name,
                "name": name,
                "base_name": re.sub(r"[（(].*?[）)]", "", name).strip(),
                "part": current_part,
                "target": split_list(target),
                "assist": split_list(assist),
                "type": type_,
                "cues": "",
                "errors": "",
                "tips": "",
                "raw": line,
            }
            continue
        if current is None:
            continue
        matched = False
        for key, prefix in FIELD_PREFIXES:
            if line.startswith(prefix + "：") or line.startswith(prefix + ":"):
                current[key] = re.split(r"[：:]", line, 1)[1].strip()
                matched = True
                break
        if not matched and current["cues"]:
            # 原始资料允许把长段落写在字段行之后。
            current["cues"] = (current["cues"] + " " + line.strip()).strip()

    flush()
    return actions


if __name__ == "__main__":
    rows = parse()
    write_jsonl(OUT, rows)
