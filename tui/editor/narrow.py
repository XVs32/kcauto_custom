"""Layout rules of the editor in narrow windows (pure functions, no Textual dependency, easy to test).

Width (columns) has three levels, from wide to narrow:
  >= 72   full: module list on the left + form on the right, one row per field
  <  72   narrow: hide the module list; show a clickable module switcher on top (ModuleTabs)
  <  50   compact: every field takes two rows (label row, value row) so the value has enough room
Dialogs additionally switch to narrow mode below width 70 (less padding, table cells laid out vertically).
"""

from __future__ import annotations

from typing import Sequence

from .model import cell_len

NARROW_WIDTH = 72  # below this the module list is hidden
COMPACT_WIDTH = 50  # below this fields become two rows
DIALOG_NARROW = 70  # below this dialogs use the narrow layout

EDITOR_HINTS: tuple[tuple[str, str], ...] = (
    ("↑↓", "move"),
    ("←→", "adjust"),
    ("enter", "edit"),
    ("space", "toggle"),
    ("d", "default"),
    ("z", "undo"),
    ("/", "search"),
    ("[ ]", "module"),
    ("w", "save"),
    ("esc", "back"),
)
# when a line does not fit, drop in this order (using the description text as the name); save / back are always kept
# hints while editing an adjustable field (second level)
EDIT_HINTS: tuple[tuple[str, str], ...] = (
    ("←→", "change"),
    ("enter", "confirm"),
    ("esc", "cancel"),
)
EDIT_HINT_DROP = ("change",)
EDITOR_HINT_DROP = (
    "module",
    "undo",
    "default",
    "toggle",
    "adjust",
    "move",
    "search",
    "edit",
)
TOP_DROP = ("badge", "file")


def row_columns(width: int, compact: bool) -> tuple[int, int]:
    """(label width, value width) of a field row. In compact mode the label and the value each take a whole line (minus the flag and indent)."""
    if compact:
        usable = max(8, width - 3)
        return usable, usable
    label = max(12, min(30, width * 2 // 5))
    return label, max(4, width - label - 5)


def tabs_layout(labels: Sequence[str], index: int, width: int) -> list[tuple[str, str]]:
    """The module switcher bar for narrow windows; returns (text, role); role: arrow / side / current / pos / gap.

    From detailed to brief, pick the first one that fits:
      ‹ combat  [ expedition ]  pvp ›
      ‹ [ expedition ] 2/11 ›
      ‹ expedition ›
    Switching modules is cyclic, so the first and last modules have neighbours wrapping to the other end.
    """
    n = len(labels)
    cur = labels[index]
    prev, nxt = labels[(index - 1) % n], labels[(index + 1) % n]
    pos = f"{index + 1}/{n}"
    options = [
        [
            ("‹ ", "arrow"),
            (prev, "side"),
            ("  ", "gap"),
            (f"[ {cur} ]", "current"),
            ("  ", "gap"),
            (nxt, "side"),
            (" ›", "arrow"),
        ],
        [
            ("‹ ", "arrow"),
            (f"[ {cur} ]", "current"),
            (f" {pos}", "pos"),
            (" ›", "arrow"),
        ],
        [("‹ ", "arrow"), (cur, "current"), (" ›", "arrow")],
    ]
    for segments in options:
        if sum(cell_len(t) for t, _ in segments) <= width:
            return segments
    return options[-1]


def tabs_centered(
    labels: Sequence[str], index: int, width: int
) -> list[tuple[str, str]]:
    """Centre the "current module"; the neighbours sit on either side and are shortened or omitted when they do not fit.

    Returns segments including spaces, with a total width not exceeding width.
    """
    n = len(labels)
    cur = f"[ {labels[index]} ]"
    cl = cell_len(cur)
    start = max(0, (width - cl) // 2)
    right_room = width - start - cl
    prev, nxt = labels[(index - 1) % n], labels[(index + 1) % n]

    def fit(label: str, room: int) -> str:
        if room < 1:
            return ""
        if cell_len(label) <= room:
            return label
        return label[: room - 1] + "…" if room >= 2 else ""

    # left: "‹ " + prev + "  "; right: "  " + nxt + " ›"
    lroom, rroom = start - 4, right_room - 4
    lp, rn = fit(prev, lroom), fit(nxt, rroom)
    if (
        lp
        and rn
        and cell_len(lp) >= min(3, cell_len(prev))
        and cell_len(rn) >= min(3, cell_len(nxt))
    ):
        left_len = 2 + cell_len(lp) + 2
        out = [
            (" " * (start - left_len), "gap"),
            ("‹ ", "arrow"),
            (lp, "side"),
            ("  ", "gap"),
            (cur, "current"),
            ("  ", "gap"),
            (rn, "side"),
            (" ›", "arrow"),
        ]
        return out
    # neighbours do not fit: arrows are fixed at the ends and the current module is centred
    if width >= cl + 4:
        return [
            ("‹", "arrow"),
            (" " * (start - 1), "gap"),
            (cur, "current"),
            (" " * max(0, right_room - 1), "gap"),
            ("›", "arrow"),
        ]
    return [(fit(labels[index], width), "current")]


def tabs_step(x: int, width: int) -> int:
    """Position clicked on the switcher → -1 (previous) / +1 (next) / 0 (middle, no action)."""
    third = max(1, width // 3)
    if x < third:
        return -1
    if x >= width - third:
        return 1
    return 0


# ---------------------------------------------------------------------- #
# ‹ › arrows on a field row (switches / enums / integers with few levels)
# ---------------------------------------------------------------------- #
ARROW_SLOT = 2  # width taken by an arrow plus a space; blanks are kept when not focused so the value does not jump


def arrow_zones(
    label_w: int, shown_w: int, compact: bool
) -> tuple[int, tuple[int, int], tuple[int, int]]:
    """Returns (row, clickable range of the left arrow, clickable range of the right arrow); ranges include both ends, x is the column within the row.

    Row layout: flag 1 + modified mark 1 + space 1, the label takes label_w, then 2 blank cells before the value
    (in compact mode the value is on the second row, indented 3 cells). Before the value is "‹ ", after it " ›".
    Each arrow's clickable range is 3 cells wide (including the neighbouring cell) so it is easy to hit with the mouse.
    """
    x0 = 3 if compact else 3 + label_w + 2
    left = x0
    right = x0 + ARROW_SLOT + shown_w + 1
    return (1 if compact else 0), (left - 1, left + 1), (right - 1, right + 1)


def arrow_hit(
    zones: tuple[int, tuple[int, int], tuple[int, int]], x: int, y: int
) -> int:
    """Click position → -1 (left arrow) / +1 (right arrow) / 0 (neither)."""
    line, (l0, l1), (r0, r1) = zones
    if y != line:
        return 0
    if l0 <= x <= l1:
        return -1
    if r0 <= x <= r1:
        return 1
    return 0
