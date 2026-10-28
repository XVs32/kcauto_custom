"""儀表板的響應式版面規劃。純函式,不依賴 Textual,方便測試。

規則(由上到下,第一個符合的生效)
  1. 橫向足夠:日誌放右側,方框欄數依剩餘寬度自動取 2~4 欄。
  2. 橫向不足、直向足夠:日誌放儀表板下方,方框欄數依寬度取 1~4 欄。
  3. 兩者都不足:隱藏日誌,方框佔滿(之後可用快捷鍵全螢幕檢視日誌)。

這些常數要和 ``theme.tcss`` 一致(``tests/test_layout.py`` 會檢查)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .modules import CARDS
from .summaries import summarize

CARD_MIN_WIDTH = 34      # 單一方框的最小寬度(含邊框與 padding)
SCROLLBAR_WIDTH = 2      # 方框區垂直捲軸可能佔用的寬度
LOG_MIN_WIDTH = 40       # 日誌在右側時的最小寬度
LOG_MIN_HEIGHT = 8       # 日誌在下方時的最小高度(含邊框)
CHROME_ROWS = 2          # 頂部狀態列 + 底部提示列
MIN_CARD_HEIGHT = 4      # 方框最小高度,對應 CSS 的 min-height
BORDER_ROWS = 2          # 方框上下邊框
MAX_COLUMNS = 4
MIN_RIGHT_COLUMNS = 2    # 日誌放右側時至少要有幾欄,否則改放下方

LOG_RIGHT = "right"
LOG_BOTTOM = "bottom"
LOG_HIDDEN = "hidden"

ALL_CLASSES = tuple(
    [f"cols-{n}" for n in range(1, MAX_COLUMNS + 1)]
    + [f"log-{p}" for p in (LOG_RIGHT, LOG_BOTTOM, LOG_HIDDEN)]
)


@dataclass(frozen=True)
class LayoutPlan:
    columns: int
    log: str

    @property
    def classes(self) -> tuple[str, str]:
        return (f"cols-{self.columns}", f"log-{self.log}")


def card_heights(values) -> list[int]:
    """依目前設定值估算每個方框的高度(順序同 ``CARDS``)。"""
    return [
        max(MIN_CARD_HEIGHT, len(summarize(spec.module, values)) + BORDER_ROWS)
        for spec in CARDS
    ]


def grid_height(heights: Sequence[int], columns: int) -> int:
    """格狀排列的總高度:每一列取該列最高的方框。"""
    total = 0
    for start in range(0, len(heights), columns):
        total += max(heights[start:start + columns])
    return total


def choose_layout(width: int, height: int, heights: Sequence[int]) -> LayoutPlan:
    # 1. 日誌在右側
    right_cols = (width - LOG_MIN_WIDTH - SCROLLBAR_WIDTH) // CARD_MIN_WIDTH
    if right_cols >= MIN_RIGHT_COLUMNS:
        return LayoutPlan(min(right_cols, MAX_COLUMNS), LOG_RIGHT)

    # 2/3. 日誌在下方或隱藏:方框用滿整個寬度
    columns = max(1, min((width - SCROLLBAR_WIDTH) // CARD_MIN_WIDTH, MAX_COLUMNS))
    needed = CHROME_ROWS + grid_height(heights, columns) + LOG_MIN_HEIGHT
    return LayoutPlan(columns, LOG_BOTTOM if needed <= height else LOG_HIDDEN)
