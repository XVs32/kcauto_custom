"""Pure Python logic of the editor (no Textual dependency, testable in a sandbox).

The screens and dialogs only display and handle keys; everything about "how a value is shown, how it is parsed, how it is searched, and whether a second confirmation is needed before changing" lives here.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from ..modules import CARDS
from ..schema.scheduler_rule import parse_rule
from ..i18n import t
from ..schema import SCHEMA, Field, Kind, Issue, fields_of

GROUP_TITLES = {
    "basic": "Basic",
    "fatigue": "Fatigue",
    "repair": "Repair",
    "routing": "Routing",
    "lbas": "LBAS",
    "ports": "Ports",
    "fleets": "Fleets",
    "resources": "Resources",
    "build": "Build",
    "develop": "Develop",
}
OTHER = (
    "other"  # last entry on the editor's left: unknown keys that are not in the schema
)


def group_title(group: str) -> str:
    return t(GROUP_TITLES.get(group, group.capitalize()))


# ---------------------------------------------------------------------- #
# text width helpers (a CJK character takes 2 cells)
# ---------------------------------------------------------------------- #
def cell_len(text: str) -> int:
    """Display width: full-width / wide characters take 2 cells, combining characters 0."""
    total = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def pad_cells(text: str, width: int) -> str:
    """Pad with spaces or truncate to the display width (an ellipsis … is appended when truncating)."""
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
# value display
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
# These "fleet preset" fields: an empty list / null / 0 all mean not used and are always shown as disable
DISABLE_KEYS = ("combat.fleet_presets", "pvp.fleet_preset", "expedition.fleet_preset")


def is_disabled_preset(field: Field, value: Any) -> bool:
    if field.key not in DISABLE_KEYS:
        return False
    if value is None or value == []:
        return True
    return isinstance(value, int) and not isinstance(value, bool) and value == 0


def format_value(field: Field, value: Any, width: int = 40) -> str:
    """One-line summary; invalid or wrongly typed values must be displayable too (the editor marks them in red)."""
    if is_disabled_preset(field, value):
        text = DISABLE
    elif value is None:
        text = "null"
    elif isinstance(value, bool):
        text = t("on") if value else t("off")
    elif (
        field.kind is Kind.INT
        and isinstance(value, int)
        and field.min is not None
        and field.max is not None
        and field.max - field.min <= 20
    ):
        text = f"{gauge(value, field.min, field.max)} {value}"
    elif field.kind is Kind.RECIPE and isinstance(value, list):
        text = " / ".join(str(v) for v in value)
    elif field.kind is Kind.LIST and isinstance(value, list):
        text = _list_summary(value, width)
    elif field.kind is Kind.OBJECT and isinstance(value, dict):
        text = (
            (t("1 entry") if len(value) == 1 else t("{n} entries", n=len(value)))
            if value
            else t("(empty)")
        )
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return clip_cells(text, width)


def _list_summary(items: list, width: int) -> str:
    if not items:
        return t("(empty)")
    joined = ", ".join(str(i) for i in items)
    if cell_len(joined) <= width:
        return joined
    return t("{n} items: {joined}", n=len(items), joined=joined)


@dataclass(frozen=True)
class HelpLine:
    text: str
    style: str = ""


def describe(
    field: Field,
    value: Any,
    default: Any,
    issues: Sequence[Issue],
    *,
    changed: bool,
    saved: Any = None,
    ignored: bool = False,
    forced_off: bool = False,
) -> list[HelpLine]:
    """Content of the bottom help panel."""
    lines = [
        HelpLine(field.key, "bold"),
        HelpLine(field.help, ""),
        HelpLine(
            t(
                "type: {type}   default: {default}   now: {now}",
                type=type_label(field),
                default=format_value(field, default, 60),
                now=format_value(field, value, 60),
            )
            + (t("   (modified)") if changed else ""),
            "#9aa0a6",
        ),
    ]
    if forced_off:
        lines.append(
            HelpLine(t("Akashi repair is off while combat is enabled"), "#6b7280")
        )
    if ignored:
        lines.append(
            HelpLine(
                t(
                    "ignored while combat.override is off — kcauto uses the defaults in data/combat"
                ),
                "#6b7280",
            )
        )
    if field.advanced:
        lines.append(
            HelpLine(
                t("advanced setting — change only if you know what it does"), "#6b7280"
            )
        )
    for issue in issues:
        style = {"error": "bold #e06c75", "danger": "bold #c678dd"}.get(
            issue.level, "#e5c07b"
        )
        lines.append(HelpLine(f"{t(issue.level)}: {issue.message}", style))
    return lines


def row_flag(issues: Sequence[Issue]) -> str:
    """Row-end flag: error / danger / warning / ''."""
    levels = {i.level for i in issues}
    for level in ("error", "danger", "warning"):
        if level in levels:
            return level
    return ""


# ---------------------------------------------------------------------- #
# module list
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


# Fields the editor does not show directly (driven by another control, e.g. the Akashi repair switch)
HIDDEN_KEYS = frozenset({"ship_switcher.slots"})


def module_keys(module: str, values: Mapping[str, Any]) -> list[str]:
    if module == OTHER:
        return unknown_keys(values)
    return [f.key for f in fields_of(module) if f.key not in HIDDEN_KEYS]


# ---------------------------------------------------------------------- #
# search
# ---------------------------------------------------------------------- #
def search_fields(query: str, limit: int = 30) -> list[Field]:
    """Search key / label / help. Key and label matches come first, then help."""
    terms = [t for t in query.lower().split() if t]
    if not terms:
        return []
    scored: list[tuple[int, int, Field]] = []
    for order, f in enumerate(SCHEMA.values()):
        if f.key in HIDDEN_KEYS:
            continue
        # Both the current language and English are searchable (English is the common wording in docs and the community)
        key = f.key.lower()
        label = (f.label + " " + f._label).lower()
        help_ = (f.help + " " + f._help).lower()
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
# second confirmation for dangerous fields
# ---------------------------------------------------------------------- #
def added_items(old: Any, new: Any) -> list[Any]:
    old_set = {str(x) for x in old} if isinstance(old, list) else set()
    if not isinstance(new, list):
        return []
    return [x for x in new if str(x) not in old_set]


def needs_danger_confirm(field: Field, old: Any, new: Any) -> bool:
    """danger fields: confirmation is only needed when an item is added that was not there before (removing is safe)."""
    if not field.danger:
        return False
    if isinstance(new, list):
        return bool(added_items(old, new))
    return bool(new) and new != old


# ---------------------------------------------------------------------- #
# parsing single-value input
# ---------------------------------------------------------------------- #
class ParseError(ValueError):
    pass


def parse_input(field: Field, text: str) -> Any:
    """Text of a dialog Input → value. Raises ParseError on failure; the range is checked by Field.validate."""
    raw = text.strip()
    if field.kind is Kind.INT:
        if not re.fullmatch(r"-?\d+", raw):
            raise ParseError(t("Enter a whole number"))
        return int(raw)
    if field.kind is Kind.INT_STR:
        if not raw:
            raise ParseError(t("Value cannot be empty"))
        return int(raw) if re.fullmatch(r"-?\d+", raw) else raw
    if field.kind is Kind.STR:
        return raw
    raise ParseError(t("Unsupported kind {kind}", kind=field.kind.value))


def check_value(field: Field, value: Any) -> Optional[str]:
    errors = field.validate(value)
    return errors[0] if errors else None


def step_int(field: Field, value: Any, delta: int) -> Optional[int]:
    """Nudge with + / -; returns None when not an integer or already at the limit."""
    if (
        field.kind is not Kind.INT
        or isinstance(value, bool)
        or not isinstance(value, int)
    ):
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
    """(display text, value). When nullable, "disabled" (null) comes first, followed by the options (e.g. disable, auto)."""
    opts: list[tuple[str, Any]] = []
    if field.nullable:
        opts.append((DISABLE, None))
    opts.extend((c, c) for c in field.choices)
    return opts


# ---------------------------------------------------------------------- #
# list (chip) editing
# ---------------------------------------------------------------------- #
def coerce_like(items: Sequence[Any], text: str) -> Any:
    """When adding an item, follow the type of the existing items: if the existing numbers are all int → convert numeric text to int."""
    text = text.strip()
    if re.fullmatch(r"\d+", text):
        existing = [i for i in items if re.fullmatch(r"\d+", str(i))]
        if existing and all(isinstance(i, int) for i in existing):
            return int(text)
    return text


def list_item_error(
    field: Field, items: Sequence[Any], candidate: Any
) -> Optional[str]:
    """After adding a candidate item to the list, return a message if it would produce an error for that item itself."""
    errors = field.validate(list(items) + [candidate])
    index = len(items) + 1
    prefix = re.escape(t("item {index}", index=index))
    for e in errors:
        if re.match(prefix + r"(?!\d)", e):
            return e
    return None


def list_length_error(field: Field, items: Sequence[Any]) -> Optional[str]:
    if not field.lengths:
        return None
    if len(items) in field.lengths:
        return None
    allowed = "/".join(str(n) for n in field.lengths)
    return t("needs exactly {allowed} item(s), has {n}", allowed=allowed, n=len(items))


# ---------------------------------------------------------------------- #
# table (multi-column) editing: node_selects / node_formations / node_night_battles
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class Column:
    name: str
    choices: tuple[
        str, ...
    ] = ()  # when there are known values, cycle through them with a menu
    optional: bool = False
    width: int = 12


@dataclass(frozen=True)
class TableSpec:
    columns: tuple[Column, ...]
    separator: str  # column separator: ">" or ":"
    note: str = ""

    def parse(self, item: Any) -> tuple[str, ...]:
        parts = str(item).split(self.separator)
        n = len(self.columns)
        if len(parts) > n:
            if self.separator == ":" and n >= 2:
                parts = parts[: n - 1] + [":".join(parts[n - 1 :])]
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
                return t("{name} is required", name=col.name)
        return None


def _formations() -> tuple[str, ...]:
    from ..schema import FORMATIONS

    return tuple(FORMATIONS)


TABLES: dict[str, TableSpec] = {
    "combat.node_selects": TableSpec(
        (Column("from"), Column("to")), ">", "Pick the next node at a branch: from > to"
    ),
    "combat.node_formations": TableSpec(
        (Column("node"), Column("formation", _formations(), width=18)),
        ":",
        "Formation used at a node",
    ),
    "combat.node_night_battles": TableSpec(
        (Column("node"), Column("night battle", ("True", "False"))),
        ":",
        "Whether to fight the night battle at a node",
    ),
    "scheduler.rules": TableSpec(
        (
            Column("condition"),
            Column("value", width=10),
            Column("action"),
            Column("module"),
            Column("extra", optional=True),
        ),
        ":",
        "condition : value : action : module [: extra]   e.g. time:0230:stop:kcauto",
    ),
}


def table_suggestions(items: Iterable[Any], spec: TableSpec) -> list[list[str]]:
    """For each column list the values that have already appeared as hints (valid scheduler values are decided by kcauto itself)."""
    seen: list[list[str]] = [[] for _ in spec.columns]
    for item in items:
        for i, cell in enumerate(spec.parse(item)):
            if cell and cell not in seen[i]:
                seen[i].append(cell)
    return seen


def check_table_row(
    field: Field,
    spec: TableSpec,
    cells: Sequence[str],
    items: Sequence[Any],
    replacing: Optional[int],
) -> Optional[str]:
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
# fleet preset
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
    """Multi-select result → list; numbers keep the existing type (int by default)."""
    as_str = [i for i in like if isinstance(i, str) and i.isdigit()]
    as_int = [i for i in like if isinstance(i, int) and not isinstance(i, bool)]
    use_str = bool(as_str) and not as_int
    out: list[Any] = []
    for t in tokens:
        out.append(int(t) if t.isdigit() and not use_str else t)
    return out


def preset_wheel_tokens(field: Field) -> list[str]:
    """Wheel entries: disable first, auto second, then 1-15."""
    return [DISABLE, "auto", *PRESET_NUMBERS]


def preset_wheel_current(field: Field, value: Any) -> str:
    """Wheel entry for the current value; empty list / null / 0 = disable; anything that does not match also falls back to disable."""
    if is_disabled_preset(field, value):
        return DISABLE
    token = str(value[0]) if isinstance(value, list) else str(value)
    return token if token in preset_wheel_tokens(field) else DISABLE


def preset_wheel_result(field: Field, token: str, like: Any = None) -> Any:
    """Wheel result → field value. List fields always write exactly one element (numbers keep the existing type);
    disable: list field = []; pvp = null (if it was 0 it stays 0, so it is not silently changed).
    """
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
# quest catalogue (quest checklist)
# ---------------------------------------------------------------------- #
# Only the top-level keys (quest IDs) of these two files are read; the first file that exists wins.
QUEST_FILES = ("data/quests/quests.json", "template/data/quests/quests.json")


@dataclass(frozen=True)
class QuestInfo:
    id: str
    note: str = ""  # e.g. "#201 daily"


def find_quest_file(root: Path | str = ".") -> Optional[Path]:
    base = Path(root)
    for rel in QUEST_FILES:
        path = base / rel
        if path.is_file():
            return path
    return None


def load_quest_catalog(root: Path | str = ".") -> list[QuestInfo]:
    """Return the quests that appear in quests.json, in file order. Returns an empty list when the file is missing or malformed."""
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


_CATEGORY = {
    "A": "composition",
    "B": "sortie",
    "C": "exercise",
    "D": "expedition",
    "E": "supply/docking",
    "F": "arsenal",
    "G": "modernization",
}
_PERIOD = {"d": "daily", "w": "weekly", "m": "monthly", "q": "quarterly", "y": "yearly"}


def quest_group(quest_id: str) -> str:
    """Bd1 → Bd; 2610B2 → 2610 (event quests are grouped by year-month); anything else → misc."""
    m = re.fullmatch(r"([A-Z][a-z]?)\d+", quest_id)
    if m:
        return m.group(1)
    m = re.fullmatch(r"(\d{4})[A-Z]\d+", quest_id)
    if m:
        return m.group(1)
    return "misc"


def quest_group_title(group: str) -> str:
    if group == "other":
        return t("other (not in quests.json)")
    if group.isdigit():
        return t("{group} · event", group=group)
    cat = _CATEGORY.get(group[:1])
    per = _PERIOD.get(group[1:])
    if cat and per:
        return f"{group} · {t(cat)} {t(per)}"
    return group


def group_quests(
    catalog: Sequence[QuestInfo | str], selected: Sequence[Any]
) -> list[tuple[str, list[str]]]:
    """Group by prefix (keeping file order); selected quests that are not in the catalogue go to 'other' so they are not silently dropped."""
    ids = [c.id if isinstance(c, QuestInfo) else str(c) for c in catalog]
    groups: dict[str, list[str]] = {}
    for qid in ids:
        groups.setdefault(quest_group(qid), []).append(qid)
    known = set(ids)
    extra = [str(x) for x in selected if str(x) not in known]
    # event quests (four-digit year-month) come first, newest first; the rest keep file order
    events = sorted(
        (g for g in groups.items() if g[0].isdigit()), key=lambda g: g[0], reverse=True
    )
    result = events + [g for g in groups.items() if not g[0].isdigit()]
    if extra:
        result.append(("other", extra))
    return result


def merge_selection(old: Sequence[Any], chosen: Iterable[str]) -> list[Any]:
    """Ticked result → list: keep the original order, newly ticked items are appended."""
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
        raise ParseError(
            t(
                "line {line}, col {col}: {msg}",
                line=exc.lineno,
                col=exc.colno,
                msg=exc.msg,
            )
        ) from exc
    if want_object and not isinstance(value, dict):
        raise ParseError(t("Must be a JSON object { ... }"))
    return value


# Resource colours (matching the in-game icons) and the recipe's 2×2 layout: top fuel/steel, bottom ammo/bauxite.
# The order in the config file is [fuel, ammo, steel, bauxite]; the layout only affects the screen, not the saved order.
# Ship types selectable for the secretary (display order); a specific ship can also be chosen by production ID.
SHIP_TYPES: tuple[
    tuple[str, str], ...
] = (  # (code, English name); the code stays English in every language
    ("DE", "Escort"),
    ("DD", "Destroyer"),
    ("CL", "Light Cruiser"),
    ("CLT", "Torpedo Cruiser"),
    ("CA", "Heavy Cruiser"),
    ("CAV", "Aviation Cruiser"),
    ("CVL", "Light Carrier"),
    ("FBB", "Fast Battleship"),
    ("BB", "Battleship"),
    ("BBV", "Aviation Battleship"),
    ("CV", "Carrier"),
    ("SS", "Submarine"),
    ("SSV", "Submarine Carrier"),
    ("AV", "Seaplane Tender"),
    ("LHA", "Amphibious Assault Ship"),
    ("CVB", "Armored Carrier"),
    ("AR", "Repair Ship"),
    ("AS", "Submarine Tender"),
    ("CT", "Training Cruiser"),
    ("AO", "Oiler"),
)
SHIP_TYPE_CODES = tuple(code for code, _ in SHIP_TYPES)
SECRETARY_ID_MAX = 999999


def is_secretary_field(field: Field) -> bool:
    return field.kind is Kind.INT_STR and field.key.endswith("_secretary")


@dataclass(frozen=True)
class RecipePreset:
    name: str
    recipe: tuple[
        int, int, int, int
    ]  # [fuel, ammo, steel, bauxite] (same order as the config file)
    secretary: Any = None  # None = no secretary specified by the preset
    comment: str = ""


RECIPE_PRESET_FILES = {
    "build": "construct_recipe_preset.json",
    "develop": "develop_recipe_preset.json",
}


def load_recipe_presets(root: Path | str, kind: str) -> list[RecipePreset]:
    """Read data/factory/{construct,develop}_recipe_preset.json (fallback template/data/factory/).

    kind = "build" | "develop". Malformed entries are skipped; an empty list is returned when no file is found.
    """
    name = RECIPE_PRESET_FILES.get(kind)
    if name is None:
        return []
    base = Path(root)
    for path in (
        base / "data" / "factory" / name,
        base / "template" / "data" / "factory" / name,
    ):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(data, dict):
            return []
        out: list[RecipePreset] = []
        for title, body in data.items():
            if not isinstance(body, dict):
                continue
            recipe = body.get(f"factory.{kind}_recipe")
            if not (
                isinstance(recipe, list)
                and len(recipe) == 4
                and all(
                    isinstance(n, int) and not isinstance(n, bool) and n >= 0
                    for n in recipe
                )
            ):
                continue
            sec = body.get(f"factory.{kind}_secretary")
            if isinstance(sec, bool) or not isinstance(sec, (int, str)):
                sec = None
            comment = body.get("comment")
            out.append(
                RecipePreset(
                    str(title),
                    tuple(recipe),
                    sec,
                    comment if isinstance(comment, str) else "",
                )
            )
        return out
    return []


def recipe_preset_row(p: RecipePreset, name_w: int = 16) -> str:
    sec = "-" if p.secretary is None else str(p.secretary)
    return f"{pad_cells(p.name, name_w)} {pad_cells('/'.join(map(str, p.recipe)), 15)} {sec}"


RESOURCES: tuple[tuple[str, str, int, int], ...] = (
    # (name, colour, row, column)
    ("fuel", "#7fc36b", 0, 0),
    ("ammo", "#b8935a", 1, 0),
    ("steel", "#9aa5b1", 0, 1),
    ("bauxite", "#e0793b", 1, 1),
)


# ---------------------------------------------------------------------- #
# numbers: wheels (digit by digit) and direct adjustment for small ranges
# ---------------------------------------------------------------------- #
SMALL_INT_SPAN = 8  # max-min ≤ 8 (at most 9 levels) counts as a "level" type field
DEFAULT_PLACES = (
    4  # for numbers without an upper limit, the minimum number of digits on the wheel
)


def is_small_int(field: Optional[Field]) -> bool:
    return (
        field is not None
        and field.kind is Kind.INT
        and field.min is not None
        and field.max is not None
        and field.max - field.min <= SMALL_INT_SPAN
    )


def adjustable(field: Optional[Field]) -> bool:
    """Fields that can be adjusted directly with ← →: switches, enums, integers with only a few levels."""
    if field is None:
        return False
    return field.kind in (Kind.BOOL, Kind.ENUM) or is_small_int(field)


def adjust_value(
    field: Field, value: Any, direction: int, *, wrap: bool = False
) -> Any:
    """Result of ← →; returns the original value when nothing changes.

    Switches and enums cycle: ← and → both flip a switch, and enums wrap around. Integers stop at the end by default; with ``wrap=True`` (Enter / Space "next") they wrap around to the other end.
    """
    if field.kind is Kind.BOOL:
        return not value
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
    """Whether it can still be adjusted in that direction (used to dim an arrow that is at its end)."""
    if field.kind in (Kind.ENUM, Kind.BOOL):  # these cycle, so both arrows always work
        return True
    return adjust_value(field, value, direction) != value


def int_options(field: Field) -> list[tuple[str, Any]]:
    return [(str(n), n) for n in range(field.min, field.max + 1)]


def number_layout(
    lo: Optional[int], hi: Optional[int], value: Any, min_places: int = 1
) -> tuple[bool, int]:
    """(has a sign wheel, number of digits). With an upper limit use its digit count; without one use at least DEFAULT_PLACES digits."""
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
# sortie map
# ---------------------------------------------------------------------- #
MAP_COUNTS = {"1": 6, "2": 5, "3": 5, "4": 5, "5": 5, "6": 5, "7": 4}
EVENT_MAPS = 9
WORLDS = ("auto", "1", "2", "3", "4", "5", "6", "7", "E")
_MAP_RE = re.compile(r"([A-Za-z0-9]+)-(\d+)(?:-([A-Za-z0-9]+))?")
NO_NODE = "—"  # the node wheel's "not specified"
NodeIndex = Mapping[tuple[str, int], Sequence[str]]


def parse_map(value: Any) -> Optional[tuple[str, Optional[int], str]]:
    """'3-5' → ('3', 5, ''); '2-2-A' → ('2', 2, 'A'); 'auto' → ('auto', None, ''); anything else → None."""
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


def map_node_items(
    nodes: Optional[NodeIndex], world: str, number: str, current: str = ""
) -> list[str]:
    """Node wheel: "—" (not specified) + the nodes that have a preset in noro6.

    A current value that is not in noro6 (preset deleted, file unreadable) is kept too, so opening the dialog does not silently change it.
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
# expeditions: set fleets 2, 3 and 4 at once
# ---------------------------------------------------------------------- #
EXPEDITION_FLEET_KEYS = (
    "expedition.fleet_2",
    "expedition.fleet_3",
    "expedition.fleet_4",
)
BULK_EXPEDITION = (
    "@expedition.all_fleets"  # virtual row, does not correspond to any config key
)

# (display name, list written to every fleet). Add a line here to add a preset.
EXPEDITION_PRESETS: tuple[tuple[str, list[str]], ...] = (
    ("auto", ["auto"]),
    ("overnight", ["overnight"]),
)
CUSTOM = "__custom__"
CLEAR = "__clear__"


def expedition_bulk_options() -> list[tuple[str, Any]]:
    opts: list[tuple[str, Any]] = [(name, name) for name, _ in EXPEDITION_PRESETS]
    opts.append((t("custom list…   (same destinations for fleets 2/3/4)"), CUSTOM))
    opts.append((t("clear all   (no expedition)"), CLEAR))
    return opts


def expedition_preset_items(name: str) -> list[str]:
    for n, items in EXPEDITION_PRESETS:
        if n == name:
            return list(items)
    return []


def expedition_common(values: Mapping[str, Any]) -> Optional[str]:
    """When the three fleets have the same setting, return the matching preset name; otherwise None."""
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
        return t("all: ") + (
            ", ".join(str(i) for i in lists[0]) if lists[0] else t("(none)")
        )
    return t("(differs per fleet)")


# ---------------------------------------------------------------------- #
# control dispatch: which dialog Enter opens for this field
# ---------------------------------------------------------------------- #
def editor_for(field: Optional[Field], value: Any = None) -> str:
    """Returns: bool | choice | choice_int | wheel | map | text | preset_wheel |
    tokens | recipe | table | quest | list | tree | json.
    """
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
        return "secretary" if is_secretary_field(field) else "text"
    if k is Kind.STR:
        return "map" if field.key == "combat.sortie_map" else "text"
    if k is Kind.PRESET:
        return "preset_wheel"
    if k is Kind.RECIPE:
        return "recipe"
    if k is Kind.OBJECT:
        return "tree"
    if field.key == "scheduler.rules":
        return "scheduler"
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
    """Value of an unknown key: single-line JSON."""
    try:
        text = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        text = repr(value)
    return clip_cells(text, width)
