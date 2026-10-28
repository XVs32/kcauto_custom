"""儀表板方框(card)的中繼資料。純 Python,不依賴 Textual,方便測試。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardSpec:
    module: str          # schema 的模組名稱,例如 "combat"
    label: str           # 顯示名稱
    hotkey: str          # 快捷字母(必須出現在 label 內)
    color: str           # 邊框強調色(hex)
    toggleable: bool = True   # 是否有 <module>.enabled 開關

    @property
    def enabled_key(self) -> str:
        return f"{self.module}.enabled"

    @property
    def card_id(self) -> str:
        return f"card-{self.module}"


# 順序即儀表板的排列順序(2 欄,由左到右、由上到下),方向鍵導覽也依此順序。
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
    """把 label 內的快捷字母標亮,例如 combat + c → ``[style]c[/]ombat``。"""
    index = label.lower().find(hotkey.lower())
    if index < 0:
        raise ValueError(f"快捷字母 {hotkey!r} 不在 {label!r} 內")
    return f"{label[:index]}[{style}]{label[index]}[/]{label[index + 1:]}"


def move_index(index: int, dx: int, dy: int, count: int = len(CARDS),
               columns: int = GRID_COLUMNS) -> int:
    """在 columns 欄的格狀排列中移動;超出邊界時維持原位。"""
    row, col = divmod(index, columns)
    new_col = col + dx
    new_row = row + dy
    if not 0 <= new_col < columns or new_row < 0:
        return index
    new_index = new_row * columns + new_col
    return new_index if new_index < count else index
