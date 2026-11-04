"""Akashi repair: the CUI only offers "on / off" for ship_switcher; the actual rules are fixed as below (taken from ship_switch.py).

On  → ``ship_switcher.enabled = True`` and ``slots`` is :data:`AKASHI_SLOTS`;
Off → ``enabled = False`` and ``slots = {}``.
Data layer, no UI dependency.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

ENABLED_KEY = "ship_switcher.enabled"
SLOTS_KEY = "ship_switcher.slots"

# Slot 1: swap the flagship (ship 187) when morale is not 0; slots 2-6: rotate damaged / undamaged ship classes
_SLOT_1 = "morale:!=:0|ship:187:>=:1:>=:0:!=:0::"
_CLASSES = [c for c in range(1, 23) if c not in (12, 15)]
_REPAIR = "damage:==:0,damage:>=:3|" + ",".join(
    f"class:{c}:!=:1:==:{n}:!=:0::" for c in _CLASSES for n in (1, 2)
)

AKASHI_SLOTS: dict[str, str] = {"1": _SLOT_1, **{str(i): _REPAIR for i in range(2, 7)}}


COMBAT_ENABLED_KEY = "combat.enabled"


def forced_off(values: Mapping[str, Any]) -> bool:
    """Akashi repair is always off while combat is enabled (the two cannot be used together)."""
    return values.get(COMBAT_ENABLED_KEY) is True


def akashi_slots() -> dict[str, str]:
    return copy.deepcopy(AKASHI_SLOTS)


def slots_for(enabled: bool, current: Any) -> Any:
    """Work out what ``slots`` should be for the given switch state.

    Keep existing (custom) rules when turning on; only fill in the Akashi defaults when empty. Turning off always clears them.
    """
    if not enabled:
        return {}
    if isinstance(current, dict) and current:
        return current
    return akashi_slots()


def state(values: Mapping[str, Any]) -> str:
    """ "off" | "akashi" | "custom" (enabled but the rules are not the Akashi defaults)."""
    if values.get(ENABLED_KEY) is not True:
        return "off"
    return "akashi" if values.get(SLOTS_KEY) == AKASHI_SLOTS else "custom"
