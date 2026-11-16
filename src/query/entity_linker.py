from __future__ import annotations
import json
import re
from pathlib import Path

from .schema import Entity, EntityType


DEFAULT_MUSCLE_ALIASES = {
    "上胸": "胸大肌上束", "中胸": "胸大肌中束", "下胸": "胸大肌下束",
    "胸肌": "胸大肌", "胸缝": "胸大肌",
    "二头": "肱二头肌", "三头": "肱三头肌", "二头肌": "肱二头肌", "三头肌": "肱三头肌",
    "背阔": "背阔肌", "斜方": "斜方肌", "菱形": "菱形肌", "竖脊": "竖脊肌",
    "前束": "三角肌前束", "中束": "三角肌中束", "后束": "三角肌后束",
    "股四": "股四头肌", "腘绳": "腘绳肌", "腹肌": "腹直肌",
    "水滴肌": "股内侧肌", "小腿": "腓肠肌", "小腿肌": "腓肠肌",
}

BODY_PART_WORDS = {
    "胸": "胸部肌群", "背": "背部肌群", "肩": "肩部肌群",
    "手臂": "手臂肌群", "胳膊": "手臂肌群",
    "腿": "腿部肌群", "臀": "臀部", "核心": "核心肌群", "腹": "核心肌群",
}

ACTION_KEYWORDS = [
    "深蹲", "卧推", "飞鸟", "划船", "推举", "弯举", "臂屈伸", "下压",
    "引体", "下拉", "硬拉", "俯卧撑", "箭步蹲", "分腿蹲", "腿举",
    "腿屈伸", "腿弯举", "提踵", "臀推", "卷腹", "举腿", "平板支撑",
    "侧平举", "前平举", "面拉", "耸肩", "山羊挺身", "夹胸", "反向飞鸟",
]

EQUIPMENT_WORDS = ["杠铃", "哑铃", "绳索", "器械", "T杠", "壶铃",
                   "弹力带", "单杠", "双杠", "史密斯"]
NEG_EQUIPMENT_WORDS = ["无器械", "没有器械", "没器械", "无器材",
                       "徒手", "自重", "居家", "家里"]
DIFFICULTY_WORDS = {"新手": "初级", "初学者": "初级", "入门": "初级",
                    "进阶": "中级", "高级": "高级", "简单": "初级", "困难": "高级"}


class EntityLinker:
    def __init__(self, parsed_dir):
        self.parsed_dir = Path(parsed_dir)
        self.muscles = self._load_jsonl(self.parsed_dir / "muscles.jsonl")
        self.actions = self._load_jsonl(self.parsed_dir / "actions.jsonl")
        self.user_muscle_aliases = self._load_json(
            self.parsed_dir / "muscle_aliases.json", {})
        self.user_action_aliases = self._load_json(
            self.parsed_dir / "action_aliases.json", {})

        self._muscle_name_to_id = {m["name"]: m["id"] for m in self.muscles}
        self._action_name_to_id = {a["name"]: a["id"] for a in self.actions}

        self.dict: dict[str, dict] = {}
        self._build_dict()

    @staticmethod
    def _load_jsonl(path: Path) -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines() if line.strip()]

    @staticmethod
    def _load_json(path: Path, default):
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _resolve_muscle_id(self, name_or_id: str) -> str | None:
        if name_or_id in self._muscle_name_to_id:
            return self._muscle_name_to_id[name_or_id]
        if name_or_id.startswith("muscle_"):
            return name_or_id
        return None

    def _add(self, word: str, canonical: str, ids: list[str],
             etype: EntityType, confidence: float = 1.0, priority: int = 0):
        word = word.strip()
        if not word:
            return
        cur = self.dict.get(word)
        if cur is None or priority > cur["priority"]:
            self.dict[word] = {"canonical": canonical, "ids": ids,
                               "type": etype, "confidence": confidence,
                               "priority": priority}

    def _build_dict(self):
        # 1. 完整动作名（优先级 100）
        for a in self.actions:
            self._add(a["name"], a["name"], [a["id"]],
                      EntityType.ACTION, 1.0, priority=100)

        # 2. 动作名去括号后的基础名 → 动作族（优先级 90）
        base_to_ids: dict[str, list[str]] = {}
        for a in self.actions:
            m = re.match(r"^(.+?)[（(]", a["name"])
            if m and m.group(1).strip() != a["name"]:
                base_to_ids.setdefault(m.group(1).strip(), []).append(a["id"])
        for base, ids in base_to_ids.items():
            self._add(base, base, ids, EntityType.ACTION_GROUP, 0.9, priority=90)

        # 3. 动作族关键词
        for kw in ACTION_KEYWORDS:
            ids = [a["id"] for a in self.actions if kw in a["name"]]
            if ids:
                self._add(kw, kw, ids, EntityType.ACTION_GROUP, 0.8, priority=85)

        # 4. 动作别名
        for alias, target in self.user_action_aliases.items():
            ids = [self._action_name_to_id.get(target, target)]
            ids = [i for i in ids if i]
            if ids:
                self._add(alias, target, ids, EntityType.ACTION, 0.95, priority=95)

        # 5. 肌肉规范名 + 内嵌 aliases
        for m in self.muscles:
            self._add(m["name"], m["name"], [m["id"]],
                      EntityType.MUSCLE, 1.0, priority=80)
            for alias in (m.get("aliases") or []):
                self._add(alias, m["name"], [m["id"]],
                          EntityType.MUSCLE, 0.95, priority=78)

        # 6. 用户肌肉别名表
        for alias, target in self.user_muscle_aliases.items():
            targets = [target] if isinstance(target, str) else list(target)
            ids = [self._resolve_muscle_id(t) for t in targets]
            ids = [i for i in ids if i]
            if ids:
                canon = targets[0] if len(targets) == 1 else alias
                etype = (EntityType.MUSCLE_GROUP
                         if alias in BODY_PART_WORDS and len(ids) > 1
                         else EntityType.MUSCLE)
                if etype == EntityType.MUSCLE_GROUP:
                    canon = BODY_PART_WORDS[alias]
                self._add(alias, canon, ids, etype, 0.95, priority=79)

        # 7. 内置兜底别名
        for alias, canon in DEFAULT_MUSCLE_ALIASES.items():
            mid = self._resolve_muscle_id(canon)
            if mid:
                self._add(alias, canon, [mid],
                          EntityType.MUSCLE, 0.85, priority=50)

        # 8. 部位词 → group / sub_group 下所有肌肉
        for word, group_name in BODY_PART_WORDS.items():
            ids = [m["id"] for m in self.muscles
                   if group_name in (m.get("group") or "")
                   or group_name in (m.get("sub_group") or "")]
            if ids:
                self._add(word, group_name, ids,
                          EntityType.MUSCLE_GROUP, 0.7, priority=30)

        # 9. 器械词 & 难度词
        for w in EQUIPMENT_WORDS:
            self._add(w, w, [], EntityType.EQUIPMENT, 1.0, priority=60)
        for w in NEG_EQUIPMENT_WORDS:
            self._add(w, w, [], EntityType.EQUIPMENT, 1.0, priority=60)
        for w, level in DIFFICULTY_WORDS.items():
            self._add(w, level, [], EntityType.DIFFICULTY, 1.0, priority=60)

    def link(self, query: str) -> list[Entity]:
        matches: list[Entity] = []
        occupied = [False] * len(query)
        for word in sorted(self.dict.keys(), key=len, reverse=True):
            meta = self.dict[word]
            start = query.find(word)
            while start != -1:
                end = start + len(word)
                if not any(occupied[start:end]):
                    matches.append(Entity(
                        text=word, start=start, end=end,
                        canonical=meta["canonical"], ids=list(meta["ids"]),
                        type=meta["type"], confidence=meta["confidence"],
                    ))
                    for i in range(start, end):
                        occupied[i] = True
                start = query.find(word, start + 1)
        return sorted(matches, key=lambda e: e.start)
