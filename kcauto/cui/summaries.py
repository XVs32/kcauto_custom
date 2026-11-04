"""Summary content of each box. Pure functions: config values → display lines, no Textual / Rich dependency.

Each line is ``(text, style)``; style is a Rich style string (empty string means default).
"""

from __future__ import annotations

from . import akashi
from .schema import ignored_by_override
from .schema.scheduler_rule import parse_rule
from typing import Any, Mapping

Line = tuple[str, str]

BAR_FULL = "█"
BAR_EMPTY = "░"

# maximum characters per line: minimum box width 34 − border/padding 4 − scrollbar 2 = 28.
# A fixed limit makes every line take exactly one row, so the layout height can be estimated in advance.
LINE_MAX = 28


def fmt_amount(value: Any) -> str:
    """350000 → 350k、1500 → 1.5k、300 → 300。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    if abs(value) >= 1000:
        return f"{value / 1000:g}k"
    return f"{value:g}"


def meter(value: Any, maximum: int, width: int = 8) -> str:
    """Text meter, e.g. ``████░░░░``. Treated as empty when not a number or when the maximum is 0."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or maximum <= 0:
        fraction = 0.0
    else:
        fraction = min(max(value / maximum, 0.0), 1.0)
    filled = round(width * fraction)
    return BAR_FULL * filled + BAR_EMPTY * (width - filled)


def _join(items: Any, empty: str = "-") -> str:
    if isinstance(items, (list, tuple)) and items:
        return ",".join(str(i) for i in items)
    return empty if not items else str(items)


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ---------------------------------------------------------------------- #
def _general(v: Mapping[str, Any]) -> list[Line]:
    jst = v["general.jst_offset"]
    jst_text = (
        f"{jst:+d}" if isinstance(jst, int) and not isinstance(jst, bool) else str(jst)
    )
    return [
        (f"mode  {v['general.interaction_mode']}", ""),
        (f"JST   {jst_text}", ""),
    ]


def _combat(v: Mapping[str, Any]) -> list[Line]:
    lines: list[Line] = [
        (f"{v['combat.sortie_map']}  {v['combat.fleet_mode']}", "bold"),
        (f"preset {_join(v['combat.fleet_presets'])}", ""),
    ]
    ignored = ignored_by_override("combat.lbas_groups", v.get("combat.override"))
    if v[
        "combat.lbas_groups"
    ]:  # these settings have no effect while override is off, so show them in grey
        lines.append(
            (f"LBAS {_join(v['combat.lbas_groups'])}", "dim" if ignored else "")
        )
    if v["combat.push_nodes"]:
        lines.append(
            (
                f"⚠ push {_join(v['combat.push_nodes'])}",
                "dim" if ignored else "bold red",
            )
        )
    return lines


def _expedition(v: Mapping[str, Any]) -> list[Line]:
    """First line: the current setting of fleets 2/3/4 (auto / overnight or destinations); second line: whether auto assign is on."""
    names = []
    for n in (2, 3, 4):
        dest = v[f"expedition.fleet_{n}"]
        names.append(_join(dest) if dest else "-")
    auto = v["expedition.fleet_preset"] == "auto"
    return [
        ("  ".join(names), "cyan"),
        ("auto assign" if auto else "no auto assign", "bold" if auto else "dim"),
    ]


def _pvp(v: Mapping[str, Any]) -> list[Line]:
    preset = v["pvp.fleet_preset"]
    return [(f"preset {'-' if preset in (None, 0) else preset}", "")]


def _quest(v: Mapping[str, Any]) -> list[Line]:
    quests = v["quest.quests"]
    count = len(quests) if isinstance(quests, list) else 0
    lines: list[Line] = [(f"{count} quest{'s' if count != 1 else ''}", "bold")]
    if count:
        shown = ",".join(str(q) for q in quests[:6])
        lines.append((_truncate(shown + ("…" if count > 6 else ""), 30), ""))
    return lines


def _factory(v: Mapping[str, Any]) -> list[Line]:
    def recipe(key: str) -> str:
        value = v[key]
        return (
            "/".join(str(x) for x in value) if isinstance(value, list) else str(value)
        )

    return [
        (f"build   {recipe('factory.build_recipe')}", ""),
        (f"develop {recipe('factory.develop_recipe')}", ""),
    ]


def _scheduler(v: Mapping[str, Any]) -> list[Line]:
    """The CUI only manages two rules: when to stop kcauto and after how many sorties to stop combat."""
    rules = v["scheduler.rules"]
    lines: list[Line] = []
    for item in rules if isinstance(rules, list) else []:
        try:
            r = parse_rule(item)
        except ValueError:
            continue
        if (
            (r.condition, r.action, r.module) == ("time", "stop", "kcauto")
            and len(r.value) == 4
            and r.value.isdigit()
        ):
            lines.append((f"stop kcauto at {r.value[:2]}:{r.value[2:]}", ""))
        elif (r.condition, r.action, r.module) == (
            "sorties_run",
            "stop",
            "combat",
        ) and r.value.isdigit():
            n = int(r.value)
            lines.append((f"stop combat at {n} sortie{'s' if n != 1 else ''}", ""))
    return lines or [("no stop rules", "dim")]


def _passive_repair(v: Mapping[str, Any]) -> list[Line]:
    return [
        (f"damage ≥ {v['passive_repair.repair_threshold']}", ""),
        (f"reserve {v['passive_repair.slots_to_reserve']} dock", ""),
    ]


def _ship_switcher(v: Mapping[str, Any]) -> list[Line]:
    state = akashi.state(v)
    if state == "akashi":
        return [("Akashi repair  on", "bold")]
    if state == "custom":
        slots = v["ship_switcher.slots"]
        n = len(slots) if isinstance(slots, dict) else 0
        return [(f"custom rules ({n} slots)", "")]
    if akashi.forced_off(v):
        return [("Akashi  off (combat on)", "dim")]
    return [("Akashi repair  off", "dim")]


def _event_reset(v: Mapping[str, Any]) -> list[Line]:
    return [
        (
            f"farm d{v['event_reset.farm_difficulty']} → "
            f"reset d{v['event_reset.reset_difficulty']}",
            "",
        ),
        (f"every {v['event_reset.frequency']} runs", ""),
    ]


_SUMMARIES = {
    "general": _general,
    "combat": _combat,
    "expedition": _expedition,
    "pvp": _pvp,
    "quest": _quest,
    "factory": _factory,
    "scheduler": _scheduler,
    "passive_repair": _passive_repair,
    "ship_switcher": _ship_switcher,
    "event_reset": _event_reset,
}


def apply_confirm_lines(
    changes: int, running: bool, new_file: bool, file_name: str
) -> list[str]:
    """What the "apply" confirmation says: what is saved and whether kcauto is started or restarted."""
    if changes:
        first = f"{changes} changed setting(s) will be saved to {file_name}"
    elif new_file:
        first = f"{file_name} will be created"
    else:
        first = "No changes to save"
    return [first, "kcauto will be restarted" if running else "kcauto will be started"]


def summarize(module: str, values: Mapping[str, Any]) -> list[Line]:
    """Return the lines to show for a module's box. Returns a hint line, never raises, when values are corrupt."""
    try:
        lines = _SUMMARIES[module](values)
    except (
        Exception
    ):  # the dashboard must not break while the user is typing an invalid value
        lines = [("(cannot display; open the editor)", "red")]
    return [(_truncate(text, LINE_MAX), style) for text, style in lines]
