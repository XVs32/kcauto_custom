"""編輯器在窄視窗下的版面規則(純函式,不依賴 Textual,方便測試)。

寬度(欄)分三級,由寬到窄:
  >= 72   完整:左側模組清單 + 右側表單,一欄一列
  <  72   窄:隱藏左側模組清單,改在上方顯示可點擊的模組切換列(ModuleTabs)
  <  50   緊湊:每個欄位佔兩列(標籤一列、值一列),值才有足夠空間顯示
對話框另外在寬度 < 70 時進入窄版(縮小留白、表格儲存格改直式排列)。
"""
from __future__ import annotations

from typing import Sequence

from .model import cell_len

NARROW_WIDTH = 72        # 低於此值隱藏模組清單
COMPACT_WIDTH = 50       # 低於此值欄位改成兩列
DIALOG_NARROW = 70       # 低於此值對話框用窄版

EDITOR_HINTS: tuple[tuple[str, str], ...] = (
    ("↑↓", "move"), ("←→", "adjust"), ("enter", "edit"), ("space", "toggle"),
    ("d", "default"), ("z", "undo"), ("/", "search"), ("[ ]", "module"),
    ("w", "save"), ("esc", "back"),
)
# 一行放不下時依序丟掉(用說明文字當名稱);save / back 永遠保留
EDITOR_HINT_DROP = ("module", "undo", "default", "toggle", "adjust", "move", "search", "edit")
TOP_DROP = ("badge", "file")


def row_columns(width: int, compact: bool) -> tuple[int, int]:
    """欄位列的 (標籤寬, 值寬)。緊湊模式標籤與值各佔整行(扣掉旗標與縮排)。"""
    if compact:
        usable = max(8, width - 3)
        return usable, usable
    label = max(12, min(30, width * 2 // 5))
    return label, max(4, width - label - 5)


def tabs_layout(labels: Sequence[str], index: int, width: int) -> list[tuple[str, str]]:
    """窄版的模組切換列,回傳 (文字, 角色);角色:arrow / side / current / pos / gap。

    由詳細到簡略,挑第一個放得下的:
      ‹ combat  [ expedition ]  pvp ›
      ‹ [ expedition ] 2/11 ›
      ‹ expedition ›
    模組切換是循環的,所以最前面與最後面的左右鄰居會接到另一端。
    """
    n = len(labels)
    cur = labels[index]
    prev, nxt = labels[(index - 1) % n], labels[(index + 1) % n]
    pos = f"{index + 1}/{n}"
    options = [
        [("‹ ", "arrow"), (prev, "side"), ("  ", "gap"), (f"[ {cur} ]", "current"),
         ("  ", "gap"), (nxt, "side"), (" ›", "arrow")],
        [("‹ ", "arrow"), (f"[ {cur} ]", "current"), (f" {pos}", "pos"), (" ›", "arrow")],
        [("‹ ", "arrow"), (cur, "current"), (" ›", "arrow")],
    ]
    for segments in options:
        if sum(cell_len(t) for t, _ in segments) <= width:
            return segments
    return options[-1]


def tabs_step(x: int, width: int) -> int:
    """點擊切換列的位置 → -1(上一個)/ +1(下一個)/ 0(中間,不動作)。"""
    third = max(1, width // 3)
    if x < third:
        return -1
    if x >= width - third:
        return 1
    return 0
