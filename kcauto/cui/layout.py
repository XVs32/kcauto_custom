"""Responsive layout planning for the dashboard. Pure functions, no Textual dependency, easy to test.

Rules (top to bottom, the first match wins)
  1. Enough width: log on the right; cards use "the fewest columns that fit" (1-4), and all spare width goes to the log.
  2. Not enough width but enough height: log below the dashboard; cards use 1-4 columns depending on width.
  3. Neither: hide the log and let the cards fill the screen (the log can later be shown full screen with a shortcut).

These constants must match ``theme.tcss`` (``tests/test_layout.py`` checks this).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .modules import CARDS
from .summaries import summarize

CARD_MIN_WIDTH = 34  # minimum width of one card (including border and padding)
SCROLLBAR_WIDTH = 2  # width the vertical scrollbar of the card area may take
LOG_MIN_WIDTH = 40  # minimum log width when it is on the right
LOG_MIN_HEIGHT = 8  # minimum log height when it is below (including border)
CHROME_ROWS = 2  # top status bar + bottom hint bar
MIN_CARD_HEIGHT = 4  # minimum card height, matches the CSS min-height
BORDER_ROWS = 2  # top and bottom card borders
MAX_COLUMNS = 4
MIN_RIGHT_COLUMNS = (
    1  # minimum number of columns when the log is on the right, otherwise it goes below
)

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
    """Estimate each card's height from the current values (same order as ``CARDS``)."""
    return [
        max(MIN_CARD_HEIGHT, len(summarize(spec.module, values)) + BORDER_ROWS)
        for spec in CARDS
    ]


def grid_height(heights: Sequence[int], columns: int) -> int:
    """Total height of the grid: each row takes the height of its tallest card."""
    total = 0
    for start in range(0, len(heights), columns):
        total += max(heights[start : start + columns])
    return total


def choose_layout(width: int, height: int, heights: Sequence[int]) -> LayoutPlan:
    # 1. Log on the right
    # Pick the fewest columns that let the cards fit the screen height; all spare width goes to the log;
    # only widen one column at a time if they do not fit (up to where the log still has LOG_MIN_WIDTH).
    right_max = min(
        (width - LOG_MIN_WIDTH - SCROLLBAR_WIDTH) // CARD_MIN_WIDTH, MAX_COLUMNS
    )
    if right_max >= MIN_RIGHT_COLUMNS:
        usable = height - CHROME_ROWS
        for columns in range(MIN_RIGHT_COLUMNS, right_max + 1):
            if grid_height(heights, columns) <= usable:
                return LayoutPlan(columns, LOG_RIGHT)
        if (
            right_max >= 2
        ):  # nothing fits: use the most columns (the card area can scroll)
            return LayoutPlan(right_max, LOG_RIGHT)
        # only one column of width and the height does not fit either → use the log-below / hidden rules

    # 2/3. Log below or hidden: cards use the full width
    columns = max(1, min((width - SCROLLBAR_WIDTH) // CARD_MIN_WIDTH, MAX_COLUMNS))
    needed = CHROME_ROWS + grid_height(heights, columns) + LOG_MIN_HEIGHT
    return LayoutPlan(columns, LOG_BOTTOM if needed <= height else LOG_HIDDEN)


def fit_segments(
    lengths: Sequence[tuple[str, int]], drop_order: Sequence[str], width: int
) -> set[str]:
    """When a line does not fit, drop the less important segments in ``drop_order`` order and return the names to keep.

    ``lengths`` is (name, display width); segments not in ``drop_order`` are always kept.
    When ``width`` <= 0 (not measured yet) everything is kept.
    """
    kept = {name for name, _ in lengths}
    if width <= 0:
        return kept
    size = dict(lengths)
    total = sum(size.values())
    for name in drop_order:
        if total <= width:
            break
        if name in kept:
            kept.discard(name)
            total -= size[name]
    return kept
