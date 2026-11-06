"""Metadata for the dashboard boxes (cards). Pure Python, no Textual dependency, easy to test."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import keymap


@dataclass(frozen=True)
class CardSpec:
    module: str  # module name in the schema, e.g. "combat"
    label: str  # display name
    hotkey: str  # shortcut key (highlighted in the label when it is one of its letters, otherwise not shown)
    color: str  # border accent colour (hex)
    toggleable: bool = True  # whether there is a <module>.enabled switch

    @property
    def enabled_key(self) -> str:
        return f"{self.module}.enabled"

    @property
    def card_id(self) -> str:
        return f"card-{self.module}"


# (module, label, colour, toggleable). The order is the dashboard order (2 columns, left to right, top to bottom);
# arrow-key navigation follows it too. The shortcut keys come from the keymap (see keymap.py).
_CARD_TABLE: tuple[tuple[str, str, str, bool], ...] = (
    ("combat", "combat", "#e06c75", True),
    ("expedition", "expedition", "#56b6c2", True),
    ("pvp", "pvp", "#98c379", True),
    ("quest", "quests", "#e5c07b", True),
    ("scheduler", "scheduler", "#c678dd", True),
    ("factory", "factory", "#d19a66", True),
    ("passive_repair", "repair", "#61afef", True),
    ("ship_switcher", "ship switcher", "#7fbbb3", True),
    ("event_reset", "event", "#f4a6c0", True),
    ("general", "general", "#abb2bf", False),
)


def make_cards(keys: Optional[keymap.Keymap] = None) -> tuple[CardSpec, ...]:
    keys = keys or keymap.active()
    return tuple(
        CardSpec(module, label, keys.module_key(module), color, toggleable)
        for module, label, color, toggleable in _CARD_TABLE
    )


CARDS: tuple[CardSpec, ...] = make_cards()

CARD_BY_MODULE = {c.module: c for c in CARDS}
GRID_COLUMNS = 2


def split_hotkey(label: str, hotkey: str) -> tuple[str, str, str]:
    """(before, highlighted, after).

    A key that is a letter of the label is highlighted in place (combat + c → "", "c", "ombat");
    any other key (a digit, ``f5``, ``space``...) is not shown at all (combat + 1 → "", "", "combat").
    """
    index = label.lower().find(hotkey.lower()) if len(hotkey) == 1 else -1
    if index < 0:
        return "", "", label
    return label[:index], label[index], label[index + 1 :]


def hotkey_markup(label: str, hotkey: str, style: str = "bold #e5c07b") -> str:
    """Rich markup of ``split_hotkey``, e.g. combat + c → ``[style]c[/]ombat``."""
    before, hot, after = split_hotkey(label, hotkey)
    if not hot:
        return after.replace("[", chr(92) + "[")
    return f"{before}[{style}]{hot.replace('[', chr(92) + '[')}[/]{after}"


# Plain text of the ON / OFF switch drawn on the bottom border (see widgets/box.py).
SWITCH_ON_TEXT = "● ON"
SWITCH_OFF_TEXT = "○ OFF"
SWITCH_HIT_PADDING = (
    4  # the spaces around the text, the corner and one column of tolerance
)


def in_toggle_zone(col: int, row: int, width: int, height: int, on: bool) -> bool:
    """Is the point inside the ON/OFF switch of a box?

    ``col`` / ``row`` are measured from the top-left corner of the box *including its border*, and
    ``width`` / ``height`` are the outer size. The switch sits on the bottom border row, right-aligned,
    so only that row and the few columns around the text count.
    """
    text = SWITCH_ON_TEXT if on else SWITCH_OFF_TEXT
    return row == height - 1 and width - len(text) - SWITCH_HIT_PADDING <= col < width


def move_index(
    index: int, dx: int, dy: int, count: int = len(CARDS), columns: int = GRID_COLUMNS
) -> int:
    """Move in a grid with the given number of columns; stay put when going past an edge."""
    row, col = divmod(index, columns)
    new_col = col + dx
    new_row = row + dy
    if not 0 <= new_col < columns or new_row < 0:
        return index
    new_index = new_row * columns + new_col
    return new_index if new_index < count else index
