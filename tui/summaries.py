"""各方框的摘要內容。純函式:設定值 → 顯示行,不依賴 Textual / Rich。

每一行是 ``(文字, 樣式)``,樣式是 Rich 樣式字串(空字串代表預設)。
"""
from __future__ import annotations

from typing import Any, Mapping

Line = tuple[str, str]

BAR_FULL = "█"
BAR_EMPTY = "░"

# 每行最多字元數:方框最小寬度 34 − 邊框/padding 4 − 捲軸 2 = 28。
# 固定上限讓每行恰好佔一列,版面高度才能事先估算。
LINE_MAX = 28


def fmt_amount(value: Any) -> str:
    """350000 → 350k、1500 → 1.5k、300 → 300。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    if abs(value) >= 1000:
        return f"{value / 1000:g}k"
    return f"{value:g}"


def meter(value: Any, maximum: int, width: int = 8) -> str:
    """文字量表,例如 ``████░░░░``。非數字或最大值為 0 時視為空。"""
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
    jst_text = f"{jst:+d}" if isinstance(jst, int) and not isinstance(jst, bool) else str(jst)
    return [
        (f"mode  {v['general.interaction_mode']}", ""),
        (f"JST   {jst_text}", ""),
    ]


def _combat(v: Mapping[str, Any]) -> list[Line]:
    lines: list[Line] = [
        (f"{v['combat.sortie_map']}  {v['combat.fleet_mode']}", "bold"),
        (f"preset {_join(v['combat.fleet_presets'])}", ""),
    ]
    if v["combat.lbas_groups"]:
        lines.append((f"LBAS {_join(v['combat.lbas_groups'])}", ""))
    if v["combat.push_nodes"]:
        lines.append((f"⚠ push {_join(v['combat.push_nodes'])}", "bold red"))
    return lines


_RESOURCES = (
    ("oil", "expedition.desire_oil", 350000),
    ("ammo", "expedition.desire_ammo", 350000),
    ("steel", "expedition.desire_steel", 350000),
    ("baux", "expedition.desire_bauxite", 350000),
    ("bkt", "expedition.desire_bucket", 3000),
)


def _expedition(v: Mapping[str, Any]) -> list[Line]:
    lines: list[Line] = []
    for name, key, maximum in _RESOURCES:
        value = v[key]
        lines.append((f"{name:<5} {meter(value, maximum)} {fmt_amount(value):>5}", "cyan"))
    fleets = " ".join(
        f"F{n} {_join(v[f'expedition.fleet_{n}'])}" for n in (2, 3, 4)
    )
    lines.append((_truncate(fleets, 30), ""))
    return lines


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
        return "/".join(str(x) for x in value) if isinstance(value, list) else str(value)

    return [
        (f"build   {recipe('factory.build_recipe')}", ""),
        (f"develop {recipe('factory.develop_recipe')}", ""),
    ]


def _scheduler(v: Mapping[str, Any]) -> list[Line]:
    rules = v["scheduler.rules"]
    count = len(rules) if isinstance(rules, list) else 0
    lines: list[Line] = [(f"{count} rule{'s' if count != 1 else ''}", "bold")]
    if isinstance(rules, list):
        lines += [(_truncate(str(r), 30), "") for r in rules[:3]]
        if count > 3:
            lines.append((f"… +{count - 3} more", "dim"))
    return lines


def _passive_repair(v: Mapping[str, Any]) -> list[Line]:
    return [
        (f"damage ≥ {v['passive_repair.repair_threshold']}", ""),
        (f"reserve {v['passive_repair.slots_to_reserve']} dock", ""),
    ]


def _ship_switcher(v: Mapping[str, Any]) -> list[Line]:
    slots = v["ship_switcher.slots"]
    count = len(slots) if isinstance(slots, dict) else 0
    return [(f"{count} slot rule{'s' if count != 1 else ''}", "")]


def _event_reset(v: Mapping[str, Any]) -> list[Line]:
    return [
        (f"farm d{v['event_reset.farm_difficulty']} → "
         f"reset d{v['event_reset.reset_difficulty']}", ""),
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


def summarize(module: str, values: Mapping[str, Any]) -> list[Line]:
    """回傳某模組方框要顯示的行。值損壞時回傳提示行,不會丟例外。"""
    try:
        lines = _SUMMARIES[module](values)
    except Exception:  # 使用者正在輸入不合法的值時,儀表板不能壞掉
        lines = [("(無法顯示,請開啟編輯器)", "red")]
    return [(_truncate(text, LINE_MAX), style) for text, style in lines]
