"""Metadata for the dashboard boxes (cards). Pure Python, no Textual dependency, easy to test."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardSpec:
    module: str  # module name in the schema, e.g. "combat"
    label: str  # display name
    hotkey: str  # shortcut letter (must appear in label)
    color: str  # border accent colour (hex)
    toggleable: bool = True  # whether there is a <module>.enabled switch

    @property
    def enabled_key(self) -> str:
        return f"{self.module}.enabled"

    @property
    def card_id(self) -> str:
        return f"card-{self.module}"


# The order is the dashboard order (2 columns, left to right, top to bottom); arrow-key navigation follows it too.
CARDS: tuple[CardSpec, ...] = (
    CardSpec("combat", "combat", "c", "#e06c75"),
    CardSpec("expedition", "expedition", "e", "#56b6c2"),
    CardSpec("pvp", "pvp", "p", "#98c379"),
    CardSpec("quest", "quests", "u", "#e5c07b"),
    CardSpec("scheduler", "scheduler", "s", "#c678dd"),
    CardSpec("factory", "factory", "f", "#d19a66"),
    CardSpec("passive_repair", "repair", "r", "#61afef"),
    CardSpec("ship_switcher", "ship switcher", "h", "#7fbbb3"),
    CardSpec("event_reset", "event", "v", "#f4a6c0"),
    CardSpec("general", "general", "g", "#abb2bf", toggleable=False),
)

CARD_BY_MODULE = {c.module: c for c in CARDS}
GRID_COLUMNS = 2


def hotkey_markup(label: str, hotkey: str, style: str = "bold #e5c07b") -> str:
    """Highlight the shortcut letter inside label, e.g. combat + c → ``[style]c[/]ombat``."""
    index = label.lower().find(hotkey.lower())
    if index < 0:
        raise ValueError(f"hotkey {hotkey!r} is not in {label!r}")
    return f"{label[:index]}[{style}]{label[index]}[/]{label[index + 1 :]}"


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
