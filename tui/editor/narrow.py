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
# 編輯某個調整型欄位(第二層)時的提示
EDIT_HINTS: tuple[tuple[str, str], ...] = (("←→", "change"), ("enter", "confirm"), ("esc", "cancel"))
EDIT_HINT_DROP = ("change",)
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


# ---------------------------------------------------------------------- #
# 欄位列上的 ‹ › 箭頭(開關 / enum / 少數等級的整數)
# ---------------------------------------------------------------------- #
ARROW_SLOT = 2           # 箭頭加空白佔用的寬度;沒聚焦時保留空白,值的位置不會跳動


def arrow_zones(label_w: int, shown_w: int, compact: bool) -> tuple[int, tuple[int, int], tuple[int, int]]:
    """回傳 (所在列, 左箭頭可點範圍, 右箭頭可點範圍),範圍含頭尾,座標為列內 x。

    列的排版:旗標 1 + 修改標記 1 + 空白 1,標籤佔 label_w,再空 2 格才是值
    (緊湊模式的值在第二列,縮排 3 格)。值前面是「‹ 」,後面是「 ›」。
    每個箭頭的可點範圍是 3 格寬(含旁邊一格),方便滑鼠點中。
    """
    x0 = 3 if compact else 3 + label_w + 2
    left = x0
    right = x0 + ARROW_SLOT + shown_w + 1
    return (1 if compact else 0), (left - 1, left + 1), (right - 1, right + 1)


def arrow_hit(zones: tuple[int, tuple[int, int], tuple[int, int]], x: int, y: int) -> int:
    """點擊位置 → -1(左箭頭)/ +1(右箭頭)/ 0(都不是)。"""
    line, (l0, l1), (r0, r1) = zones
    if y != line:
        return 0
    if l0 <= x <= l1:
        return -1
    if r0 <= x <= r1:
        return 1
    return 0
