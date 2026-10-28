"""編輯器的純 Python 邏輯(不依賴 Textual,可在沙盒測試)。

畫面與對話框只負責顯示與按鍵,所有「值怎麼顯示、怎麼解析、怎麼搜尋、
修改前要不要二次確認」都在這裡。
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from ..modules import CARDS
from ..schema import SCHEMA, Field, Kind, Issue, fields_of
from ..schema.scheduler_rule import parse_rule

GROUP_TITLES = {
    "basic": "Basic", "fatigue": "Fatigue", "repair": "Repair",
    "routing": "Routing", "lbas": "LBAS", "ports": "Ports",
    "fleets": "Fleets", "resources": "Resources",
    "build": "Build", "develop": "Develop",
}
OTHER = "other"     # 編輯器左側最後一項:schema 沒有的未知 key


def group_title(group: str) -> str:
    return GROUP_TITLES.get(group, group.capitalize())


# ---------------------------------------------------------------------- #
# 文字寬度工具(中文字佔 2 格)
# ---------------------------------------------------------------------- #
def cell_len(text: str) -> int:
    """顯示寬度:全形/寬字元 2 格,組合字元 0 格。"""
    total = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def pad_cells(text: str, width: int) -> str:
    """依顯示寬度補空白或截斷(截斷時結尾加 …)。"""
    if width <= 0:
        return ""
    length = cell_len(text)
    if length <= width:
        return text + " " * (width - length)
    out = ""
    for ch in text:
        if cell_len(out + ch) > width - 1:
            break
        out += ch
    return out + "…" + " " * max(0, width - cell_len(out) - 1)


def clip_cells(text: str, width: int) -> str:
    return pad_cells(text, width).rstrip() if width > 0 else ""


# ---------------------------------------------------------------------- #
# 值的顯示
# ---------------------------------------------------------------------- #
def gauge(value: int, lo: int, hi: int, width: int = 8) -> str:
    if hi <= lo:
        return ""
    ratio = min(max((value - lo) / (hi - lo), 0.0), 1.0)
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


def type_label(field: Field) -> str:
    k = field.kind
    if k is Kind.INT:
        if field.min is not None and field.max is not None:
            return f"int {field.min}..{field.max}"
        if field.min is not None:
            return f"int ≥{field.min}"
        return "int"
    if k is Kind.INT_STR:
        return "int | str"
    if k is Kind.ENUM:
        names = list(field.choices) + (["null"] if field.nullable else [])
        return "enum " + "/".join(names)
    if k is Kind.PRESET:
        return "preset 1..15 | auto" + (" | null" if field.nullable else "")
    if k is Kind.RECIPE:
        return "recipe [fuel, ammo, steel, bauxite]"
    if k is Kind.LIST:
        extra = ""
        if field.lengths:
            extra = " (len " + "/".join(str(n) for n in field.lengths) + ")"
        return "list" + extra
    return k.value


DISABLE = "disable"
# 這幾個「艦隊 preset」欄位:空清單 / null / 0 都表示不使用,一律顯示成 disable
DISABLE_KEYS = ("combat.fleet_presets", "pvp.fleet_preset", "expedition.fleet_preset")


def is_disabled_preset(field: Field, value: Any) -> bool:
    if field.key not in DISABLE_KEYS:
        return False
    if value is None or value == []:
        return True
    return isinstance(value, int) and not isinstance(value, bool) and value == 0


def format_value(field: Field, value: Any, width: int = 40) -> str:
    """單行摘要;不合法或型別不符的值也要能顯示(編輯器會用紅字標示)。"""
    if is_disabled_preset(field, value):
        text = DISABLE
    elif value is None:
        text = "null"
    elif isinstance(value, bool):
        text = "on" if value else "off"
    elif field.kind is Kind.INT and isinstance(value, int) and field.min is not None \
            and field.max is not None and field.max - field.min <= 20:
        text = f"{gauge(value, field.min, field.max)} {value}"
    elif field.kind is Kind.RECIPE and isinstance(value, list):
        text = " / ".join(str(v) for v in value)
    elif field.kind is Kind.LIST and isinstance(value, list):
        text = _list_summary(value, width)
    elif field.kind is Kind.OBJECT and isinstance(value, dict):
        text = f"{len(value)} entr{'y' if len(value) == 1 else 'ies'}" if value else "(empty)"
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return clip_cells(text, width)


def _list_summary(items: list, width: int) -> str:
    if not items:
        return "(empty)"
    joined = ", ".join(str(i) for i in items)
    if cell_len(joined) <= width:
        return joined
    return f"{len(items)} items: {joined}"


@dataclass(frozen=True)
class HelpLine:
    text: str
    style: str = ""


def describe(field: Field, value: Any, default: Any, issues: Sequence[Issue],
             *, changed: bool, saved: Any = None) -> list[HelpLine]:
    """底部說明面板的內容。"""
    lines = [
        HelpLine(field.key, "bold"),
        HelpLine(field.help, ""),
        HelpLine(
            f"type: {type_label(field)}   default: {format_value(field, default, 60)}"
            f"   now: {format_value(field, value, 60)}" + ("   (modified)" if changed else ""),
            "#9aa0a6",
        ),
    ]
    if field.advanced:
        lines.append(HelpLine("advanced setting — change only if you know what it does", "#6b7280"))
    for issue in issues:
        style = {"error": "bold #e06c75", "danger": "bold #c678dd"}.get(issue.level, "#e5c07b")
        lines.append(HelpLine(f"{issue.level}: {issue.message}", style))
    return lines


def row_flag(issues: Sequence[Issue]) -> str:
    """列尾旗標:error / danger / warning / ''。"""
    levels = {i.level for i in issues}
    for level in ("error", "danger", "warning"):
        if level in levels:
            return level
    return ""


# ---------------------------------------------------------------------- #
# 模組清單
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class ModuleEntry:
    module: str
    label: str
    hotkey: str
    color: str


MODULE_ENTRIES: tuple[ModuleEntry, ...] = tuple(
    ModuleEntry(c.module, c.label, c.hotkey, c.color) for c in CARDS
) + (ModuleEntry(OTHER, "other", "o", "#7f848e"),)


def unknown_keys(values: Mapping[str, Any]) -> list[str]:
    return [k for k in values if k not in SCHEMA]


def module_keys(module: str, values: Mapping[str, Any]) -> list[str]:
    if module == OTHER:
        return unknown_keys(values)
    return [f.key for f in fields_of(module)]


# ---------------------------------------------------------------------- #
# 搜尋
# ---------------------------------------------------------------------- #
def search_fields(query: str, limit: int = 30) -> list[Field]:
    """搜尋 key / 標籤 / 說明。key 與標籤命中優先,其次說明。"""
    terms = [t for t in query.lower().split() if t]
    if not terms:
        return []
    scored: list[tuple[int, int, Field]] = []
    for order, f in enumerate(SCHEMA.values()):
        key, label, help_ = f.key.lower(), f.label.lower(), f.help.lower()
        score = 0
        for t in terms:
            if t in f.name.lower():
                score += 4 if f.name.lower().startswith(t) else 3
            elif t in key:
                score += 2
            elif t in label:
                score += 3
            elif t in help_:
                score += 1
            else:
                score = -1
                break
        if score > 0:
            scored.append((-score, order, f))
    scored.sort(key=lambda s: (s[0], s[1]))
    return [f for _, _, f in scored[:limit]]


# ---------------------------------------------------------------------- #
# 危險欄位的二次確認
# ---------------------------------------------------------------------- #
def added_items(old: Any, new: Any) -> list[Any]:
    old_set = {str(x) for x in old} if isinstance(old, list) else set()
    if not isinstance(new, list):
        return []
    return [x for x in new if str(x) not in old_set]


def needs_danger_confirm(field: Field, old: Any, new: Any) -> bool:
    """danger 欄位:只有「新增了原本沒有的項目」才需要確認(移除是安全的)。"""
    if not field.danger:
        return False
    if isinstance(new, list):
        return bool(added_items(old, new))
    return bool(new) and new != old


# ---------------------------------------------------------------------- #
# 單值輸入解析
# ---------------------------------------------------------------------- #
class ParseError(ValueError):
    pass


def parse_input(field: Field, text: str) -> Any:
    """對話框 Input 的文字 → 值。解析失敗丟 ParseError;範圍由 Field.validate 判斷。"""
    raw = text.strip()
    if field.kind is Kind.INT:
        if not re.fullmatch(r"-?\d+", raw):
            raise ParseError("Enter a whole number")
        return int(raw)
    if field.kind is Kind.INT_STR:
        if not raw:
            raise ParseError("Value cannot be empty")
        return int(raw) if re.fullmatch(r"-?\d+", raw) else raw
    if field.kind is Kind.STR:
        return raw
    raise ParseError(f"Unsupported kind {field.kind.value}")


def check_value(field: Field, value: Any) -> Optional[str]:
    errors = field.validate(value)
    return errors[0] if errors else None


def step_int(field: Field, value: Any, delta: int) -> Optional[int]:
    """+ / - 微調;不是整數或已到邊界時回傳 None。"""
    if field.kind is not Kind.INT or isinstance(value, bool) or not isinstance(value, int):
        return None
    new = value + delta
    if field.min is not None:
        new = max(new, field.min)
    if field.max is not None:
        new = min(new, field.max)
    return None if new == value else new


def cycle_choice(options: Sequence[Any], current: Any, step: int = 1) -> Any:
    if not options:
        return current
    try:
        index = list(options).index(current)
    except ValueError:
        return options[0]
    return options[(index + step) % len(options)]


def enum_options(field: Field) -> list[tuple[str, Any]]:
    """(顯示文字, 值)。nullable 時「停用」(null)放第一項,接著才是各選項(例如 disable、auto)。"""
    opts: list[tuple[str, Any]] = []
    if field.nullable:
        opts.append((DISABLE, None))
    opts.extend((c, c) for c in field.choices)
    return opts


# ---------------------------------------------------------------------- #
# 清單(chip)編輯
# ---------------------------------------------------------------------- #
def coerce_like(items: Sequence[Any], text: str) -> Any:
    """新增項目時,沿用既有項目的型別:既有的數字都是 int → 數字文字轉 int。"""
    text = text.strip()
    if re.fullmatch(r"\d+", text):
        existing = [i for i in items if re.fullmatch(r"\d+", str(i))]
        if existing and all(isinstance(i, int) for i in existing):
            return int(text)
    return text


def list_item_error(field: Field, items: Sequence[Any], candidate: Any) -> Optional[str]:
    """候選項目加進清單後,若會產生「該項目本身」的錯誤就回傳訊息。"""
    errors = field.validate(list(items) + [candidate])
    index = len(items) + 1
    for e in errors:
        if e.startswith(f"第 {index} 項"):
            return e
    return None


def list_length_error(field: Field, items: Sequence[Any]) -> Optional[str]:
    if not field.lengths:
        return None
    if len(items) in field.lengths:
        return None
    allowed = "/".join(str(n) for n in field.lengths)
    return f"needs exactly {allowed} item(s), has {len(items)}"


# ---------------------------------------------------------------------- #
# 表格(多欄)編輯:node_selects / node_formations / node_night_battles / scheduler.rules
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class Column:
    name: str
    choices: tuple[str, ...] = ()       # 有值時以選單循環輸入
    optional: bool = False
    width: int = 12


@dataclass(frozen=True)
class TableSpec:
    columns: tuple[Column, ...]
    separator: str                      # 欄位分隔字元:">" 或 ":"
    note: str = ""

    def parse(self, item: Any) -> tuple[str, ...]:
        parts = str(item).split(self.separator)
        n = len(self.columns)
        if len(parts) > n:
            if self.separator == ":" and n >= 2:
                parts = parts[: n - 1] + [":".join(parts[n - 1:])]
            else:
                parts = parts[:n]
        parts += [""] * (n - len(parts))
        return tuple(p.strip() for p in parts)

    def format(self, cells: Sequence[str]) -> str:
        cells = [c.strip() for c in cells]
        while cells and not cells[-1] and self.columns[len(cells) - 1].optional:
            cells.pop()
        return self.separator.join(cells)

    def missing(self, cells: Sequence[str]) -> Optional[str]:
        for col, cell in zip(self.columns, cells):
            if not cell.strip() and not col.optional:
                return f"{col.name} is required"
        return None


def _formations() -> tuple[str, ...]:
    from ..schema import FORMATIONS
    return tuple(FORMATIONS)


TABLES: dict[str, TableSpec] = {
    "combat.node_selects": TableSpec(
        (Column("from"), Column("to")), ">",
        "Pick the next node at a branch: from > to"),
    "combat.node_formations": TableSpec(
        (Column("node"), Column("formation", _formations(), width=18)), ":",
        "Formation used at a node"),
    "combat.node_night_battles": TableSpec(
        (Column("node"), Column("night battle", ("True", "False"))), ":",
        "Whether to fight the night battle at a node"),
    "scheduler.rules": TableSpec(
        (Column("condition"), Column("value", width=10), Column("action"),
         Column("module"), Column("extra", optional=True)), ":",
        "condition : value : action : module [: extra]   e.g. time:0230:stop:kcauto"),
}


def table_suggestions(items: Iterable[Any], spec: TableSpec) -> list[list[str]]:
    """每欄把「目前已出現過的值」列出來當提示(scheduler 的合法值由 kcauto 本體決定)。"""
    seen: list[list[str]] = [[] for _ in spec.columns]
    for item in items:
        for i, cell in enumerate(spec.parse(item)):
            if cell and cell not in seen[i]:
                seen[i].append(cell)
    return seen


def check_table_row(field: Field, spec: TableSpec, cells: Sequence[str],
                    items: Sequence[Any], replacing: Optional[int]) -> Optional[str]:
    problem = spec.missing(cells)
    if problem:
        return problem
    text = spec.format(cells)
    if field.key == "scheduler.rules":
        try:
            parse_rule(text)
        except ValueError as exc:
            return str(exc)
        return None
    base = [x for i, x in enumerate(items) if i != replacing]
    return list_item_error(field, base, text)


# ---------------------------------------------------------------------- #
# 艦隊 preset
# ---------------------------------------------------------------------- #
PRESET_NUMBERS = tuple(str(n) for n in range(1, 16))


def preset_tokens(*, multi: bool, nullable: bool) -> list[str]:
    tokens = list(PRESET_NUMBERS) + ["auto"]
    if not multi:
        if nullable:
            tokens.append("null")
        tokens.append("0")
    return tokens


def preset_selection(value: Any) -> list[str]:
    if value is None:
        return ["null"]
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def preset_value(tokens: Sequence[str], like: Sequence[Any] = ()) -> list[Any]:
    """多選結果 → 清單,數字沿用既有型別(預設 int)。"""
    as_str = [i for i in like if isinstance(i, str) and i.isdigit()]
    as_int = [i for i in like if isinstance(i, int) and not isinstance(i, bool)]
    use_str = bool(as_str) and not as_int
    out: list[Any] = []
    for t in tokens:
        out.append(int(t) if t.isdigit() and not use_str else t)
    return out


def preset_wheel_tokens(field: Field) -> list[str]:
    """滾輪的項目:disable 第一,auto 第二,接著 1~15。"""
    return [DISABLE, "auto", *PRESET_NUMBERS]


def preset_wheel_current(field: Field, value: Any) -> str:
    """目前值對應的滾輪項目;空清單 / null / 0 = disable;對不上時也回到 disable。"""
    if is_disabled_preset(field, value):
        return DISABLE
    token = str(value[0]) if isinstance(value, list) else str(value)
    return token if token in preset_wheel_tokens(field) else DISABLE


def preset_wheel_result(field: Field, token: str, like: Any = None) -> Any:
    """滾輪結果 → 欄位值。清單欄位固定只寫一個元素(數字沿用既有型別);
    disable:清單欄位 = [];pvp = null(原本是 0 就維持 0,不悄悄改掉)。"""
    if field.kind is Kind.LIST:
        if token == DISABLE:
            return []
        return preset_value([token], like if isinstance(like, list) else [])
    if token == DISABLE:
        if isinstance(like, int) and not isinstance(like, bool) and like == 0:
            return 0
        return None if field.nullable else 0
    return preset_single_value(token)


def preset_single_value(token: str) -> Any:
    if token == "null":
        return None
    if token == "auto":
        return "auto"
    return int(token)


def has_duplicates(items: Sequence[Any]) -> bool:
    texts = [str(i) for i in items]
    return len(set(texts)) != len(texts)


# ---------------------------------------------------------------------- #
# 任務目錄(quest 勾選清單)
# ---------------------------------------------------------------------- #
# 只讀這兩個檔案的「頂層 key」(任務 ID);第一個存在的檔案為準。
QUEST_FILES = ("data/quests/quests.json", "template/data/quests/quests.json")


@dataclass(frozen=True)
class QuestInfo:
    id: str
    note: str = ""          # 例如 "#201 daily"


def find_quest_file(root: Path | str = ".") -> Optional[Path]:
    base = Path(root)
    for rel in QUEST_FILES:
        path = base / rel
        if path.is_file():
            return path
    return None


def load_quest_catalog(root: Path | str = ".") -> list[QuestInfo]:
    """依檔案順序回傳 quests.json 內有出現的任務。找不到或格式不對時回傳空清單。"""
    path = find_quest_file(root)
    if path is None:
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    out: list[QuestInfo] = []
    for qid, body in data.items():
        if not isinstance(qid, str) or not isinstance(body, dict):
            continue
        bits = []
        if isinstance(body.get("id"), int):
            bits.append(f"#{body['id']}")
        if isinstance(body.get("type"), str):
            bits.append(body["type"])
        out.append(QuestInfo(qid, " ".join(bits)))
    return out


_CATEGORY = {"A": "composition", "B": "sortie", "C": "exercise", "D": "expedition",
             "E": "supply/docking", "F": "arsenal", "G": "modernization"}
_PERIOD = {"d": "daily", "w": "weekly", "m": "monthly", "q": "quarterly", "y": "yearly"}


def quest_group(quest_id: str) -> str:
    """Bd1 → Bd;2610B2 → 2610(活動任務依年月分組);其他 → misc。"""
    m = re.fullmatch(r"([A-Z][a-z]?)\d+", quest_id)
    if m:
        return m.group(1)
    m = re.fullmatch(r"(\d{4})[A-Z]\d+", quest_id)
    if m:
        return m.group(1)
    return "misc"


def quest_group_title(group: str) -> str:
    if group == "other":
        return "other (not in quests.json)"
    if group.isdigit():
        return f"{group} · event"
    cat = _CATEGORY.get(group[:1])
    per = _PERIOD.get(group[1:])
    if cat and per:
        return f"{group} · {cat} {per}"
    return group


def group_quests(catalog: Sequence[QuestInfo | str],
                 selected: Sequence[Any]) -> list[tuple[str, list[str]]]:
    """依前綴分組(保持檔案順序);已選但不在目錄的歸到 'other',避免被悄悄丟掉。"""
    ids = [c.id if isinstance(c, QuestInfo) else str(c) for c in catalog]
    groups: dict[str, list[str]] = {}
    for qid in ids:
        groups.setdefault(quest_group(qid), []).append(qid)
    known = set(ids)
    extra = [str(x) for x in selected if str(x) not in known]
    result = list(groups.items())
    if extra:
        result.append(("other", extra))
    return result


def merge_selection(old: Sequence[Any], chosen: Iterable[str]) -> list[Any]:
    """勾選結果 → 清單:保留原本的順序,新勾的接在後面。"""
    chosen = list(chosen)
    chosen_set = set(chosen)
    out = [x for x in old if str(x) in chosen_set]
    have = {str(x) for x in out}
    out.extend(c for c in chosen if c not in have)
    return out


# ---------------------------------------------------------------------- #
# JSON
# ---------------------------------------------------------------------- #
def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def parse_json(text: str, *, want_object: bool = False) -> Any:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"line {exc.lineno}, col {exc.colno}: {exc.msg}") from exc
    if want_object and not isinstance(value, dict):
        raise ParseError("Must be a JSON object { ... }")
    return value


# 資源配色(對應遊戲內的圖示色)與配方的 2×2 排版:上 燃料/鋼材,下 彈藥/鋁土。
# 設定檔內的順序是 [燃料, 彈藥, 鋼材, 鋁土],排版只影響畫面,不影響存檔順序。
RESOURCES: tuple[tuple[str, str, int, int], ...] = (
    # (名稱, 顏色, 排, 欄)
    ("fuel", "#7fc36b", 0, 0),
    ("ammo", "#b8935a", 1, 0),
    ("steel", "#9aa5b1", 0, 1),
    ("bauxite", "#e0793b", 1, 1),
)


# ---------------------------------------------------------------------- #
# 數字:滾輪(逐位數)與小範圍直接調整
# ---------------------------------------------------------------------- #
SMALL_INT_SPAN = 8          # max-min ≤ 8(最多 9 個等級)視為「等級」型欄位
DEFAULT_PLACES = 4          # 沒有上限的數字,滾輪至少幾位


def is_small_int(field: Optional[Field]) -> bool:
    return (field is not None and field.kind is Kind.INT
            and field.min is not None and field.max is not None
            and field.max - field.min <= SMALL_INT_SPAN)


def adjustable(field: Optional[Field]) -> bool:
    """可以直接用 ← → 調整的欄位:開關、enum、只有幾個等級的整數。"""
    if field is None:
        return False
    return field.kind in (Kind.BOOL, Kind.ENUM) or is_small_int(field)


def adjust_value(field: Field, value: Any, direction: int, *, wrap: bool = False) -> Any:
    """← → 的結果;沒有變化時回傳原值。

    開關:→ = on、← = off。enum 循環。整數預設到頭就停;``wrap=True``(Enter / Space
    「往下一個」)時到頭會繞回另一端。
    """
    if field.kind is Kind.BOOL:
        return (not value) if wrap else direction > 0
    if field.kind is Kind.ENUM:
        return cycle_choice([v for _, v in enum_options(field)], value, direction)
    new = step_int(field, value, direction)
    if new is None and wrap and field.kind is Kind.INT and _is_plain_int(value):
        new = field.min if direction > 0 else field.max
        if new is None or new == value:
            new = None
    return value if new is None else new


def _is_plain_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def can_adjust(field: Field, value: Any, direction: int) -> bool:
    """該方向還能不能再調(用來把到頭的箭頭顯示成暗色)。"""
    if field.kind is Kind.ENUM:
        return True
    return adjust_value(field, value, direction) != value


def int_options(field: Field) -> list[tuple[str, Any]]:
    return [(str(n), n) for n in range(field.min, field.max + 1)]


def number_layout(lo: Optional[int], hi: Optional[int], value: Any,
                  min_places: int = 1) -> tuple[bool, int]:
    """(是否有正負號輪, 位數)。有上限就用上限的位數;沒有上限至少 DEFAULT_PLACES 位。"""
    signed = lo is not None and lo < 0
    nums = [abs(v) for v in (lo, hi) if isinstance(v, int)]
    if isinstance(value, int) and not isinstance(value, bool):
        nums.append(abs(value))
    longest = max((len(str(n)) for n in nums), default=1)
    if hi is None:
        longest = max(longest, DEFAULT_PLACES)
    return signed, max(longest, min_places)


def digits_of(value: int, places: int) -> list[int]:
    return [int(c) for c in str(abs(value)).zfill(places)[-places:]]


def number_from(negative: bool, digits: Sequence[int]) -> int:
    n = int("".join(str(d) for d in digits) or "0")
    return -n if negative else n


def clamp_number(value: int, lo: Optional[int], hi: Optional[int]) -> int:
    if lo is not None:
        value = max(value, lo)
    if hi is not None:
        value = min(value, hi)
    return value


# ---------------------------------------------------------------------- #
# 出擊海域
# ---------------------------------------------------------------------- #
MAP_COUNTS = {"1": 6, "2": 5, "3": 5, "4": 5, "5": 5, "6": 5, "7": 4}
EVENT_MAPS = 9
WORLDS = ("auto", "1", "2", "3", "4", "5", "6", "7", "E")
_MAP_RE = re.compile(r"([A-Za-z0-9]+)-(\d+)(?:-([A-Za-z0-9]+))?")
NO_NODE = "—"                       # 節點滾輪的「不指定」
NodeIndex = Mapping[tuple[str, int], Sequence[str]]


def parse_map(value: Any) -> Optional[tuple[str, Optional[int], str]]:
    """'3-5' → ('3', 5, '');'2-2-A' → ('2', 2, 'A');'auto' → ('auto', None, '');不符 → None。"""
    if value == "auto":
        return "auto", None, ""
    if isinstance(value, str):
        m = _MAP_RE.fullmatch(value)
        if m:
            return m.group(1), int(m.group(2)), m.group(3) or ""
    return None


def world_items(current: Optional[str] = None) -> list[str]:
    items = list(WORLDS)
    if current and current not in items:
        items.append(current)
    return items


def map_number_items(world: str, current: Optional[int] = None) -> list[str]:
    if world == "auto":
        return ["—"]
    count = MAP_COUNTS.get(world, EVENT_MAPS)
    if current is not None:
        count = max(count, current)
    return [str(n) for n in range(1, count + 1)]


def map_node_items(nodes: Optional[NodeIndex], world: str, number: str,
                   current: str = "") -> list[str]:
    """節點滾輪:「—」(不指定)+ noro6 內有指定該節點預設的節點。

    目前值若不在 noro6 內(預設被刪、檔案讀不到)也保留,避免打開就被悄悄改掉。
    """
    items = [NO_NODE]
    if world != "auto" and number.isdigit() and nodes:
        items += [n for n in nodes.get((world, int(number)), ()) if n not in items]
    if current and current not in items:
        items.append(current)
    return items


def build_map(world: str, number: str, node: str = "") -> str:
    if world == "auto":
        return "auto"
    return f"{world}-{number}" + (f"-{node}" if node and node != NO_NODE else "")


# ---------------------------------------------------------------------- #
# 遠征:一次設定 2、3、4 艦隊
# ---------------------------------------------------------------------- #
EXPEDITION_FLEET_KEYS = ("expedition.fleet_2", "expedition.fleet_3", "expedition.fleet_4")
BULK_EXPEDITION = "@expedition.all_fleets"      # 虛擬列,不對應任何設定 key

# (顯示名稱, 寫進每個艦隊的清單)。要增加預設就在這裡加一行。
EXPEDITION_PRESETS: tuple[tuple[str, list[str]], ...] = (
    ("auto", ["auto"]),
    ("overnight", ["overnight"]),
)
CUSTOM = "__custom__"
CLEAR = "__clear__"


def expedition_bulk_options() -> list[tuple[str, Any]]:
    opts: list[tuple[str, Any]] = [(name, name) for name, _ in EXPEDITION_PRESETS]
    opts.append(("custom list…   (same destinations for fleets 2/3/4)", CUSTOM))
    opts.append(("clear all   (no expedition)", CLEAR))
    return opts


def expedition_preset_items(name: str) -> list[str]:
    for n, items in EXPEDITION_PRESETS:
        if n == name:
            return list(items)
    return []


def expedition_common(values: Mapping[str, Any]) -> Optional[str]:
    """三個艦隊的設定一致時,回傳對應的預設名稱;否則 None。"""
    lists = [values.get(k) for k in EXPEDITION_FLEET_KEYS]
    if not all(isinstance(x, list) for x in lists) or any(x != lists[0] for x in lists):
        return None
    for name, items in EXPEDITION_PRESETS:
        if lists[0] == items:
            return name
    return None


def bulk_summary(values: Mapping[str, Any]) -> str:
    lists = [values.get(k) for k in EXPEDITION_FLEET_KEYS]
    if all(isinstance(x, list) for x in lists) and all(x == lists[0] for x in lists):
        return "all: " + (", ".join(str(i) for i in lists[0]) if lists[0] else "(none)")
    return "(differs per fleet)"


# ---------------------------------------------------------------------- #
# 控制項分派:這個欄位按 Enter 要開哪種對話框
# ---------------------------------------------------------------------- #
def editor_for(field: Optional[Field], value: Any = None) -> str:
    """回傳:bool | choice | choice_int | wheel | map | text | preset_wheel |
    tokens | recipe | table | quest | list | tree | json。"""
    if field is None:
        return "json"
    k = field.kind
    if k is Kind.BOOL:
        return "bool"
    if k is Kind.ENUM:
        return "choice"
    if k is Kind.INT:
        return "choice_int" if is_small_int(field) else "wheel"
    if k in (Kind.INT_STR,):
        return "text"
    if k is Kind.STR:
        return "map" if field.key == "combat.sortie_map" else "text"
    if k is Kind.PRESET:
        return "preset_wheel"
    if k is Kind.RECIPE:
        return "recipe"
    if k is Kind.OBJECT:
        return "tree"
    if field.key in TABLES:
        return "table"
    if field.key == "quest.quests":
        return "quest"
    if field.key == "combat.fleet_presets":
        return "preset_wheel"
    if field.key == "combat.lbas_groups":
        return "tokens"
    return "list"


def format_raw(value: Any, width: int = 40) -> str:
    """未知 key 的值:單行 JSON。"""
    try:
        text = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        text = repr(value)
    return clip_cells(text, width)
