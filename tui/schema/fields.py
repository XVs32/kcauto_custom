"""Config field definitions for kcauto_custom (per Wiki Ch5, 63 keys in total).

This schema is the single source of truth for the CUI:
  * The editor picks the control by ``kind``, groups by ``group``, and shows ``label`` / ``help``.
  * ``Field.validate`` validates a single field; cross-field rules are in ``rules.py``.
  * Fields marked ``advanced`` are folded on the dashboard by default; ``danger`` fields need a second confirmation before changing.

Adding a setting only needs one more entry in ``_FIELDS``; ``tests/test_schema.py`` compares the Ch5 field list and fails when one is missing.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

from .. import i18n
from ..i18n import t
from .scheduler_rule import check_rule


class Kind(str, Enum):
    BOOL = "bool"  # switch
    ENUM = "enum"  # single choice (may be nullable)
    INT = "int"  # integer with a range
    INT_STR = (
        "int_str"  # integer or string (e.g. secretary ship ID, both spellings allowed)
    )
    STR = "str"  # string (may carry a pattern)
    LIST = "list"  # array of strings / integers
    PRESET = "preset"  # 1-15, "auto" or None (fleet preset)
    RECIPE = "recipe"  # 4 integers [fuel, ammo, steel, bauxite]
    OBJECT = "object"  # any JSON object


MODULES = (
    "general",
    "combat",
    "expedition",
    "pvp",
    "quest",
    "factory",
    "scheduler",
    "passive_repair",
    "ship_switcher",
    "event_reset",
)

FORMATIONS = (
    "line_ahead",
    "double_line",
    "diamond",
    "echelon",
    "line_abreast",
    "vanguard",
    "combined_fleet_1",
    "combined_fleet_2",
    "combined_fleet_3",
    "combined_fleet_4",
)
FLEET_MODES = ("standard", "strike", "tcf", "ctf", "stf")
COMBINED_FLEET_MODES = ("tcf", "ctf", "stf")
INTERACTION_MODES = ("chrome_driver", "direct_control", "poi")

_NODE = r"[A-Za-z0-9_]+"
_ID = r"[A-Za-z0-9_]+"
_PRESET_ITEM = r"auto|[1-9]|1[0-5]"


def _is_int(value: Any) -> bool:
    # bool is a subclass of int and must be excluded
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class Field:
    key: str
    kind: Kind
    default: Any
    _label: str  # English (the default language); other languages are in tui/locales
    _help: str
    group: str = "basic"
    choices: tuple = ()  # valid values of ENUM
    nullable: bool = False  # whether ENUM / PRESET allows None
    min: Optional[int] = None  # lower bound of INT / RECIPE elements
    max: Optional[int] = None  # upper bound of INT / RECIPE elements
    pattern: Optional[str] = None  # regex for the whole STR, or for each LIST element
    pattern_hint: str = ""  # format hint shown when the pattern does not match
    lengths: tuple = ()  # allowed LIST lengths (empty = unlimited)
    item_check: Optional[Callable[[Any], Optional[str]]] = None
    advanced: bool = False
    danger: bool = False

    @property
    def label(self) -> str:
        return i18n.field_text(self.key, "label", self._label)

    @property
    def help(self) -> str:
        return i18n.field_text(self.key, "help", self._help)

    @property
    def module(self) -> str:
        return self.key.split(".", 1)[0]

    @property
    def name(self) -> str:
        return self.key.split(".", 1)[1]

    def make_default(self) -> Any:
        return copy.deepcopy(self.default)

    def _hint(self) -> str:
        text = t(self.pattern_hint or "format mismatch")
        return text.replace("{formations}", "/".join(FORMATIONS))

    # ------------------------------------------------------------------ #
    def validate(self, value: Any) -> list[str]:
        """Return a list of error messages; an empty list means valid."""
        check = getattr(self, f"_check_{self.kind.value}")
        return check(value)

    def _check_bool(self, value: Any) -> list[str]:
        return [] if isinstance(value, bool) else [t("must be true or false")]

    def _check_enum(self, value: Any) -> list[str]:
        if value is None:
            return [] if self.nullable else [t("cannot be null")]
        if value in self.choices and isinstance(value, str):
            return []
        return [t("must be one of: {choices}", choices=t(", ").join(self.choices))]

    def _check_int(self, value: Any) -> list[str]:
        if not _is_int(value):
            return [t("must be an integer")]
        return self._range_errors(value)

    def _range_errors(self, value: int) -> list[str]:
        if self.min is not None and value < self.min:
            return [t("must be at least {min}", min=self.min)]
        if self.max is not None and value > self.max:
            return [t("must be at most {max}", max=self.max)]
        return []

    def _check_int_str(self, value: Any) -> list[str]:
        if _is_int(value):
            return self._range_errors(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return [t("cannot be an empty string")]
            if re.fullmatch(
                r"-?\d+", text
            ):  # "1234" counts as an integer, and the range applies
                return self._range_errors(int(text))
            return []
        return [t("must be an integer or a string")]

    def _check_str(self, value: Any) -> list[str]:
        if not isinstance(value, str):
            return [t("must be a string")]
        if self.pattern and not re.fullmatch(self.pattern, value):
            return [self._hint()]
        return []

    def _check_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return [t("must be an array")]
        errors: list[str] = []
        if self.lengths and len(value) not in self.lengths:
            allowed = t(", ").join(str(n) for n in self.lengths)
            errors.append(
                t(
                    "item count must be {allowed} (currently {n})",
                    allowed=allowed,
                    n=len(value),
                )
            )
        for index, item in enumerate(value, start=1):
            if isinstance(item, bool) or not isinstance(item, (str, int)):
                errors.append(
                    t("item {index} must be a string or an integer", index=index)
                )
                continue
            if self.pattern and not re.fullmatch(self.pattern, str(item)):
                errors.append(
                    t(
                        'item {index} "{item}": {message}',
                        index=index,
                        item=item,
                        message=self._hint(),
                    )
                )
            if self.item_check is not None:
                message = self.item_check(item)
                if message:
                    errors.append(
                        t(
                            'item {index} "{item}": {message}',
                            index=index,
                            item=item,
                            message=t(message),
                        )
                    )
        return errors

    def _check_preset(self, value: Any) -> list[str]:
        if value is None:
            return [] if self.nullable else [t("cannot be null")]
        if value == "auto":
            return []
        # 0 is the documented default (meaning unspecified), so 0-15 is allowed
        if _is_int(value) and 0 <= value <= 15:
            return []
        return [t("must be 1-15, auto or null")]

    def _check_recipe(self, value: Any) -> list[str]:
        if not isinstance(value, list) or len(value) != 4:
            return [t("must be 4 integers [fuel, ammo, steel, bauxite]")]
        errors = []
        for label, item in zip((t("fuel"), t("ammo"), t("steel"), t("bauxite")), value):
            if not _is_int(item):
                errors.append(t("{label} must be an integer", label=label))
            else:
                errors.extend(f"{label} {e}" for e in self._range_errors(item))
        return errors

    def _check_object(self, value: Any) -> list[str]:
        return [] if isinstance(value, dict) else [t("must be a JSON object")]


# ---------------------------------------------------------------------- #
# small helpers for building fields
# ---------------------------------------------------------------------- #
def _bool(key, default, label, help, **kw):
    return Field(key, Kind.BOOL, default, label, help, **kw)


def _int(key, default, label, help, **kw):
    return Field(key, Kind.INT, default, label, help, **kw)


def _int_str(key, default, label, help, **kw):
    return Field(key, Kind.INT_STR, default, label, help, **kw)


def _enum(key, default, label, help, choices, **kw):
    return Field(key, Kind.ENUM, default, label, help, choices=tuple(choices), **kw)


def _list(key, label, help, **kw):
    return Field(key, Kind.LIST, [], label, help, **kw)


_NODE_HINT = "Node names: letters, digits and underscores only"

_FIELDS: tuple[Field, ...] = (
    # ------------------------------ general ------------------------------ #
    _enum(
        "general.interaction_mode",
        "chrome_driver",
        "Interaction mode",
        "How kcauto talks to the game: chrome_driver (Chrome DevTools), direct_control (desktop mouse), or poi (POI API Forwarder plugin).",
        INTERACTION_MODES,
    ),
    _int(
        "general.jst_offset",
        0,
        "JST offset (hours)",
        "Offset from Japan Standard Time used for scheduling and time-based actions.",
        min=-20,
        max=20,
    ),
    _int(
        "general.chrome_dev_port",
        9222,
        "Chrome DevTools port",
        "Port used by the Chrome DevTools Protocol. Leave as is if unsure.",
        group="ports",
        min=0,
        max=65535,
        advanced=True,
    ),
    _int(
        "general.poi_api_port",
        9223,
        "POI API port",
        "Port used by the POI API forwarder. Leave as is if unsure.",
        group="ports",
        min=0,
        max=65535,
        advanced=True,
    ),
    _int(
        "general.poi_control_port",
        38591,
        "POI control port",
        "Local port used for screenshots and input when interaction_mode is poi.",
        group="ports",
        min=0,
        max=65535,
        advanced=True,
    ),
    _bool(
        "general.paused",
        False,
        "Start paused",
        "Whether kcauto starts paused. Currently has no effect (per the wiki, 2025/07/17); use Space in the CUI to pause.",
        advanced=True,
    ),
    # ------------------------------- combat ------------------------------ #
    _bool(
        "combat.enabled",
        False,
        "Enable combat",
        "Whether the combat module is enabled.",
    ),
    Field(
        "combat.sortie_map",
        Kind.STR,
        "1-1",
        "Sortie map",
        "Map number such as 1-1, 3-5, 6-4 or E-1, optionally followed by a target node such as 2-2-A or 7-2-G (needs a matching noro6 preset). Use auto to pick the map automatically.",
        pattern=r"auto|[A-Za-z0-9]+-\d+(-[A-Za-z0-9]+)?",
        pattern_hint="Use a map number such as 1-1, E-1 or 2-2-A, or auto",
    ),
    _enum(
        "combat.fleet_mode",
        "standard",
        "Fleet mode",
        "standard: single fleet; strike: strike force (uses fleet 3); tcf: transport escort; ctf: carrier task force; stf: surface task force.",
        FLEET_MODES,
    ),
    _list(
        "combat.fleet_presets",
        "Fleet preset",
        "In-game fleet preset (1-15) used for sorties, or auto to choose automatically.",
        pattern=_PRESET_ITEM,
        pattern_hint="Must be 1-15 or auto",
    ),
    _bool(
        "combat.check_fatigue",
        True,
        "Check fatigue",
        "Whether to check ship morale before sortie.",
        group="fatigue",
    ),
    _bool(
        "combat.check_lbas_fatigue",
        True,
        "Check LBAS fatigue",
        "Whether to check land-base air corps (LBAS) fatigue before sortie.",
        group="fatigue",
    ),
    _bool(
        "combat.clear_stop",
        False,
        "Stop after map clear",
        "Whether to stop sortieing once the map is cleared.",
    ),
    _bool(
        "combat.paused_after_fleetswitch",
        False,
        "Pause after ship switch",
        "Pause after a ship switch so you can adjust the fleet and equipment yourself. "
        "Only pauses when true.",
    ),
    _bool(
        "combat.port_check",
        False,
        "Check port capacity",
        "Whether to check port capacity before sortie.",
    ),
    _bool(
        "combat.reserve_repair_dock",
        True,
        "Reserve repair dock",
        "Whether to keep a repair dock free for emergency repairs.",
        group="repair",
    ),
    _int(
        "combat.retreat_limit",
        4,
        "Retreat damage level",
        "Retreat when this damage level is reached. 0 none, 1 scratch, 2 light, 3 moderate, 4 heavy.",
        group="repair",
        min=0,
        max=4,
    ),
    _int(
        "combat.repair_limit",
        3,
        "Repair damage level",
        "Repair automatically when this damage level is reached.",
        group="repair",
        min=0,
        max=4,
    ),
    _int(
        "combat.repair_bucket_threshold",
        500,
        "Bucket reserve",
        "Do not use repair buckets when fewer than this many remain.",
        group="repair",
        min=0,
    ),
    _int(
        "combat.repair_timelimit_hours",
        0,
        "Natural repair limit (hours)",
        "Use a bucket only if repair takes longer than this; added to the minutes.",
        group="repair",
        min=0,
    ),
    _int(
        "combat.repair_timelimit_minutes",
        0,
        "Natural repair limit (minutes)",
        "Use a bucket only if repair takes longer than this many minutes.",
        group="repair",
        min=0,
        max=59,
    ),
    _list(
        "combat.retreat_points",
        "Retreat nodes",
        "Node names where the fleet should retreat, e.g. A, B, C.",
        group="routing",
        pattern=_NODE,
        pattern_hint=_NODE_HINT,
    ),
    _list(
        "combat.push_nodes",
        "Push-on nodes (dangerous)",
        "Nodes where the fleet advances regardless of damage. Advancing with heavily damaged ships can sink them; use with care.",
        group="routing",
        pattern=_NODE,
        pattern_hint=_NODE_HINT,
        danger=True,
    ),
    _list(
        "combat.node_selects",
        "Branch routing",
        "Route choices at branch points, formatted from>to, e.g. A>B.",
        group="routing",
        pattern=rf"{_NODE}>{_NODE}",
        pattern_hint="Use from>to, e.g. A>B",
    ),
    _list(
        "combat.node_formations",
        "Node formations",
        "Formation used at each node, formatted node:formation, e.g. A:line_ahead.",
        group="routing",
        pattern=rf"{_NODE}:(?:{'|'.join(FORMATIONS)})",
        pattern_hint="Use node:formation; formation must be one of: {formations}",
    ),
    _list(
        "combat.node_night_battles",
        "Node night battles",
        "Whether to fight a night battle at each node, formatted node:True or node:False.",
        group="routing",
        pattern=rf"{_NODE}:(?:True|False)",
        pattern_hint="Use node:True or node:False",
    ),
    _list(
        "combat.node_smoke",
        "Smoke nodes",
        "Node names where a smoke generator is used.",
        group="routing",
        pattern=_NODE,
        pattern_hint=_NODE_HINT,
    ),
    _list(
        "combat.lbas_groups",
        "Active LBAS groups",
        "Land-base air corps numbers to activate (1, 2, 3).",
        group="lbas",
        pattern=r"[1-3]",
        pattern_hint="Must be 1, 2 or 3",
    ),
    _list(
        "combat.lbas_group_1_nodes",
        "LBAS 1 target nodes",
        "Targets of land-base air corps 1: exactly 0 or 2 nodes, e.g. A, A.",
        group="lbas",
        pattern=_NODE,
        pattern_hint=_NODE_HINT,
        lengths=(0, 2),
    ),
    _list(
        "combat.lbas_group_2_nodes",
        "LBAS 2 target nodes",
        "Targets of land-base air corps 2: exactly 0 or 2 nodes.",
        group="lbas",
        pattern=_NODE,
        pattern_hint=_NODE_HINT,
        lengths=(0, 2),
    ),
    _list(
        "combat.lbas_group_3_nodes",
        "LBAS 3 target nodes",
        "Targets of land-base air corps 3: exactly 0 or 2 nodes.",
        group="lbas",
        pattern=_NODE,
        pattern_hint=_NODE_HINT,
        lengths=(0, 2),
    ),
    _bool(
        "combat.override",
        False,
        "Allow config override",
        "Set false to use default combat settings in data/combat",
        advanced=True,
    ),
    # ----------------------------- expedition ---------------------------- #
    _bool(
        "expedition.enabled",
        True,
        "Enable expeditions",
        "Whether the expedition module is enabled.",
    ),
    _list(
        "expedition.fleet_2",
        "Fleet 2 expeditions",
        "Expedition numbers for fleet 2, or auto to choose automatically.",
        group="fleets",
        pattern=_ID,
        pattern_hint="Letters, digits and underscores only",
    ),
    _list(
        "expedition.fleet_3",
        "Fleet 3 expeditions",
        "Expedition numbers for fleet 3, or auto to choose automatically.",
        group="fleets",
        pattern=_ID,
        pattern_hint="Letters, digits and underscores only",
    ),
    _list(
        "expedition.fleet_4",
        "Fleet 4 expeditions",
        "Expedition numbers for fleet 4, or auto to choose automatically.",
        group="fleets",
        pattern=_ID,
        pattern_hint="Letters, digits and underscores only",
    ),
    Field(
        "expedition.fleet_preset",
        Kind.ENUM,
        None,
        "Fleet preset mode",
        "Currently only auto or not used (null) is supported.",
        group="fleets",
        choices=("auto",),
        nullable=True,
    ),
    _int(
        "expedition.desire_oil",
        350000,
        "Fuel target",
        "Fuel amount expeditions should maintain.",
        group="resources",
        min=0,
        max=350000,
    ),
    _int(
        "expedition.desire_ammo",
        350000,
        "Ammo target",
        "Ammo amount expeditions should maintain.",
        group="resources",
        min=0,
        max=350000,
    ),
    _int(
        "expedition.desire_steel",
        350000,
        "Steel target",
        "Steel amount expeditions should maintain.",
        group="resources",
        min=0,
        max=350000,
    ),
    _int(
        "expedition.desire_bauxite",
        350000,
        "Bauxite target",
        "Bauxite amount expeditions should maintain.",
        group="resources",
        min=0,
        max=350000,
    ),
    _int(
        "expedition.desire_bucket",
        3000,
        "Bucket target",
        "Repair bucket amount expeditions should maintain.",
        group="resources",
        min=0,
        max=3000,
    ),
    _int(
        "expedition.desire_devmat",
        3000,
        "Dev. material target",
        "Development material amount expeditions should maintain.",
        group="resources",
        min=0,
        max=3000,
    ),
    # -------------------------------- pvp -------------------------------- #
    _bool(
        "pvp.enabled",
        False,
        "Enable PvP",
        "Whether to run exercises (PvP). Cannot be enabled while the sortie fleet is a combined fleet.",
    ),
    Field(
        "pvp.fleet_preset",
        Kind.PRESET,
        0,
        "PvP fleet preset",
        "Fleet preset (1-15), auto or null used for PvP.",
        nullable=True,
    ),
    # ------------------------------- quest ------------------------------- #
    _bool(
        "quest.enabled",
        True,
        "Enable quests",
        "Whether to accept and complete quests automatically.",
    ),
    _list(
        "quest.quests",
        "Quest list",
        "IDs of quests to accept and complete automatically, e.g. Bd1, Bw1, C2.",
        pattern=_ID,
        pattern_hint="Letters, digits and underscores only",
    ),
    # ------------------------------ factory ------------------------------ #
    _bool(
        "factory.enabled",
        False,
        "Enable factory",
        "Whether construction and development are enabled.",
    ),
    Field(
        "factory.build_recipe",
        Kind.RECIPE,
        [30, 30, 30, 30],
        "Construction recipe",
        "Resource recipe for building ships [fuel, ammo, steel, bauxite].",
        group="build",
        min=0,
    ),
    _int_str(
        "factory.build_secretary",
        1234,
        "Construction secretary",
        "Secretary ship used when building: a ship type or a production ID.",
        group="build",
        min=0,
    ),
    Field(
        "factory.develop_recipe",
        Kind.RECIPE,
        [10, 10, 10, 10],
        "Development recipe",
        "Resource recipe for developing equipment [fuel, ammo, steel, bauxite].",
        group="develop",
        min=0,
    ),
    _int_str(
        "factory.develop_secretary",
        1234,
        "Development secretary",
        "Secretary ship used when developing: a ship type or a production ID.",
        group="develop",
        min=0,
    ),
    # ----------------------------- scheduler ----------------------------- #
    _bool(
        "scheduler.enabled",
        True,
        "Enable scheduler",
        "Whether the scheduler is enabled.",
    ),
    _list(
        "scheduler.rules",
        "Schedule",
        "The CUI manages two rules only: when to stop kcauto (time:HHMM:stop:kcauto) and how many sorties before combat stops (sorties_run:N:stop:combat).",
        item_check=check_rule,
    ),
    # --------------------------- passive_repair -------------------------- #
    _bool(
        "passive_repair.enabled",
        False,
        "Enable passive repair",
        "Whether automatic repair-dock management is enabled.",
    ),
    _int(
        "passive_repair.repair_threshold",
        1,
        "Repair damage level",
        "Passive repair triggers at this damage level (1-4).",
        min=1,
        max=4,
    ),
    _int(
        "passive_repair.slots_to_reserve",
        2,
        "Docks to reserve",
        "Number of repair docks kept free for emergency repairs.",
        min=0,
    ),
    # --------------------------- ship_switcher --------------------------- #
    _bool(
        "ship_switcher.enabled",
        False,
        "Akashi repair",
        "On: use the Akashi-repair ship switching rules (swap out damaged ships; rules are fixed). Off: disable ship switching and clear the rules.",
    ),
    Field(
        "ship_switcher.slots",
        Kind.OBJECT,
        {},
        "Switch rules",
        "Per-slot ship switching rules (JSON object).",
        advanced=True,
    ),
    # ---------------------------- event_reset ---------------------------- #
    _bool(
        "event_reset.enabled",
        False,
        "Enable event reset",
        "Whether event-map reset is enabled.",
    ),
    _int(
        "event_reset.farm_difficulty",
        2,
        "Farming difficulty",
        "Difficulty used while farming (1-4).",
        min=1,
        max=4,
    ),
    _int(
        "event_reset.reset_difficulty",
        3,
        "Reset difficulty",
        "Difficulty to reset to after farming (1-4).",
        min=1,
        max=4,
    ),
    _int(
        "event_reset.frequency",
        3,
        "Reset frequency",
        "Trigger a reset after this many farming runs.",
        min=0,
    ),
)

SCHEMA: dict[str, Field] = {f.key: f for f in _FIELDS}
if len(SCHEMA) != len(_FIELDS):  # pragma: no cover - development-time guard
    raise RuntimeError("duplicate key in schema")


def fields_of(module: str) -> list[Field]:
    """Return a module's fields in schema order."""
    return [f for f in _FIELDS if f.module == module]


def groups_of(module: str) -> list[str]:
    """Return a module's group names (in order of appearance)."""
    seen: list[str] = []
    for f in fields_of(module):
        if f.group not in seen:
            seen.append(f.group)
    return seen


def defaults() -> dict[str, Any]:
    return {f.key: f.make_default() for f in _FIELDS}
