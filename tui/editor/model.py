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


def format_value(field: Field, value: Any, width: int = 40) -> str:
    """單行摘要;不合法或型別不符的值也要能顯示(編輯器會用紅字標示)。"""
    if value is None:
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
    """(顯示文字, 值)。nullable 時最前面加 null。"""
    opts: list[tuple[str, Any]] = []
    if field.nullable:
        opts.append(("null  (disabled)", None))
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
QUEST_ID = re.compile(r"[A-Z][a-z]{0,2}\d{1,3}")


def _walk_ids(node: Any, out: list[str]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and QUEST_ID.fullmatch(k) and k not in out:
                out.append(k)
            _walk_ids(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_ids(v, out)
    elif isinstance(node, str) and QUEST_ID.fullmatch(node) and node not in out:
        out.append(node)


def load_quest_catalog(root: Path | str = "data") -> list[str]:
    """掃描 data/ 底下檔名含 quest 的 JSON,收集符合任務 ID 格式的名稱。

    找不到或格式不認得時回傳空清單,畫面會退回一般的清單編輯器。
    """
    base = Path(root)
    found: list[str] = []
    if not base.is_dir():
        return found
    for path in sorted(base.rglob("*.json")):
        if "quest" not in path.name.lower() and "quest" not in str(path.parent).lower():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        _walk_ids(data, found)
    return found


def quest_group(quest_id: str) -> str:
    m = re.match(r"[A-Z][a-z]{0,2}", quest_id)
    return m.group(0) if m else "?"


def group_quests(catalog: Sequence[str], selected: Sequence[Any]) -> list[tuple[str, list[str]]]:
    """依前綴分組(Bd、Bw、C…);已選但不在目錄的歸到 'other'。"""
    groups: dict[str, list[str]] = {}
    known = set(catalog)
    for q in catalog:
        groups.setdefault(quest_group(q), []).append(q)
    extra = [str(s) for s in selected if str(s) not in known]
    result = [(g, sorted(ids, key=_natural)) for g, ids in groups.items()]
    if extra:
        result.append(("other", extra))
    return result


def _natural(text: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"(\d+)", text))


def merge_selection(old: Sequence[Any], chosen: Iterable[str]) -> list[Any]:
    """勾選結果 → 清單:保留原本的順序,新勾的接在後面。"""
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


# ---------------------------------------------------------------------- #
# 控制項分派:這個欄位按 Enter 要開哪種對話框
# ---------------------------------------------------------------------- #
def editor_for(field: Optional[Field], value: Any = None) -> str:
    """回傳 'bool'|'choice'|'text'|'preset'|'preset_list'|'recipe'|'table'|'quest'|'list'|'json'。"""
    if field is None:
        return "json"
    k = field.kind
    if k is Kind.BOOL:
        return "bool"
    if k is Kind.ENUM:
        return "choice"
    if k in (Kind.INT, Kind.INT_STR, Kind.STR):
        return "text"
    if k is Kind.PRESET:
        return "preset"
    if k is Kind.RECIPE:
        return "recipe"
    if k is Kind.OBJECT:
        return "json"
    if field.key in TABLES:
        return "table"
    if field.key == "quest.quests":
        return "quest"
    if field.key == "combat.fleet_presets":
        return "preset_list"
    return "list"


def format_raw(value: Any, width: int = 40) -> str:
    """未知 key 的值:單行 JSON。"""
    try:
        text = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        text = repr(value)
    return clip_cells(text, width)
