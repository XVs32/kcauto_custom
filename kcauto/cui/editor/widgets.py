"""Small widgets for the editor: lists, cycling menus, preset grids, clickable button labels.

Everything is drawn by hand (render) instead of relying on Textual's built-in OptionList / Button / Select, so the look is consistent and not affected by API differences between versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from rich.text import Text
from textual import events
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from .model import cell_len

CURSOR_STYLE = "bold #e8eaed on #3a4150"
DIM = "#6b7280"
GREEN = "#98c379"
YELLOW = "#e5c07b"


@dataclass
class Row:
    text: str
    selectable: bool = True
    checked: Optional[bool] = None  # None: no checkbox is drawn
    toggle: bool = False  # a click / Space "toggles" instead of "selects"
    style: str = ""


class PickList(Widget, can_focus=True):
    """Scrollable single-column list. Up/Down move; Enter selects; Space toggles the tick."""

    BINDINGS = [
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("pageup", "page(-1)", show=False),
        Binding("pagedown", "page(1)", show=False),
        Binding("home", "jump(0)", show=False),
        Binding("end", "jump(1)", show=False),
        Binding("enter", "choose", show=False),
        Binding("space", "toggle", show=False),
    ]

    class Chosen(Message):
        def __init__(self, source: "PickList", index: int) -> None:
            super().__init__()
            self.source = source
            self.index = index

    class Toggled(Message):
        def __init__(self, source: "PickList", index: int) -> None:
            super().__init__()
            self.source = source
            self.index = index

    class Moved(Message):
        """The cursor moved to another item (used to update the path row, previews, etc. live)."""

        def __init__(self, source: "PickList", index: int) -> None:
            super().__init__()
            self.source = source
            self.index = index

    class Edge(Message):
        """Pressed outward while already on the first / last item: direction = -1 / +1."""

        def __init__(self, source: "PickList", direction: int) -> None:
            super().__init__()
            self.source = source
            self.direction = direction

    def __init__(
        self,
        rows: Sequence[Row] = (),
        *,
        max_visible: int = 10,
        empty: str = "(empty)",
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.max_visible = max_visible
        self.empty = empty
        self.rows: list[Row] = []
        self.cursor = 0
        self._top = 0
        self.set_rows(rows)

    # ------------------------------------------------------------------ #
    def set_rows(self, rows: Sequence[Row], cursor: int | None = None) -> None:
        self.rows = list(rows)
        if cursor is not None:
            self.cursor = cursor
        self.cursor = self._nearest_selectable(self.cursor)
        self.styles.height = max(1, min(len(self.rows), self.max_visible))
        self.refresh()

    def _nearest_selectable(self, index: int) -> int:
        n = len(self.rows)
        if n == 0:
            return 0
        index = min(max(index, 0), n - 1)
        for d in range(n):
            for j in (index + d, index - d):
                if 0 <= j < n and self.rows[j].selectable:
                    return j
        return index

    @property
    def current(self) -> Optional[Row]:
        return self.rows[self.cursor] if 0 <= self.cursor < len(self.rows) else None

    def move_cursor(self, delta: int, *, edge: bool = False) -> bool:
        """Move |delta| selectable items in the direction of delta; returns whether it moved."""
        step = 1 if delta > 0 else -1
        i, remaining = self.cursor, abs(delta)
        while remaining:
            j = i + step
            while 0 <= j < len(self.rows) and not self.rows[j].selectable:
                j += step
            if not 0 <= j < len(self.rows):
                break
            i, remaining = j, remaining - 1
        if i == self.cursor:
            if edge:
                self.post_message(self.Edge(self, step))
            return False
        self.cursor = i
        self.refresh()
        self.post_message(self.Moved(self, i))
        return True

    # ------------------------------------------------------------------ #
    def action_move(self, delta: int) -> None:
        self.move_cursor(delta, edge=True)

    def action_page(self, direction: int) -> None:
        self.move_cursor(direction * max(1, self.max_visible - 1))

    def action_jump(self, end: int) -> None:
        if not self.rows:
            return
        target = len(self.rows) - 1 if end else 0
        self.cursor = self._nearest_selectable(target)
        self.refresh()
        self.post_message(self.Moved(self, self.cursor))

    def action_choose(self) -> None:
        if self.current is not None and self.current.selectable:
            self.post_message(self.Chosen(self, self.cursor))

    def action_toggle(self) -> None:
        if self.current is not None and self.current.toggle:
            self.post_message(self.Toggled(self, self.cursor))

    def on_click(self, event: events.Click) -> None:
        index = self._top + event.y
        if not 0 <= index < len(self.rows) or not self.rows[index].selectable:
            return
        event.stop()
        self.cursor = index
        self.focus()
        self.refresh()
        self.post_message(self.Moved(self, index))
        row = self.rows[index]
        if row.toggle:
            self.post_message(self.Toggled(self, index))
        else:
            self.post_message(self.Chosen(self, index))

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        event.stop()
        event.prevent_default()
        self.move_cursor(-3)

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        event.stop()
        event.prevent_default()
        self.move_cursor(3)

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    # ------------------------------------------------------------------ #
    def render(self) -> Text:
        if not self.rows:
            return Text(self.empty, style=DIM)
        visible = max(1, min(len(self.rows), self.max_visible))
        if self.cursor < self._top:
            self._top = self.cursor
        elif self.cursor >= self._top + visible:
            self._top = self.cursor - visible + 1
        self._top = max(0, min(self._top, len(self.rows) - visible))
        width = max(self.size.width, 10)

        text = Text(no_wrap=True, overflow="ellipsis")
        for i in range(self._top, self._top + visible):
            row = self.rows[i]
            line = Text(no_wrap=True, overflow="ellipsis")
            if row.checked is not None:
                line.append(
                    "[x] " if row.checked else "[ ] ",
                    style=GREEN if row.checked else DIM,
                )
            line.append(row.text, style=row.style)
            if i == self.cursor and row.selectable:
                line.pad_right(max(0, width - line.cell_len))
                line.stylize(CURSOR_STYLE if self.has_focus else "on #2a2f3a")
            text.append_text(line)
            if i < self._top + visible - 1:
                text.append("\n")
        return text


# ---------------------------------------------------------------------- #
class CycleBox(Widget, can_focus=True):
    """Input cell that cycles through fixed options with ←/→ or Space. Enter submits."""

    BINDINGS = [
        Binding("left", "cycle(-1)", show=False),
        Binding("right", "cycle(1)", show=False),
        Binding("space", "cycle(1)", show=False),
        Binding("enter", "submit", show=False),
    ]

    class Submitted(Message):
        def __init__(self, source: "CycleBox") -> None:
            super().__init__()
            self.source = source

    def __init__(
        self, options: Sequence[str], *, value: str | None = None, id: str | None = None
    ) -> None:
        super().__init__(id=id)
        self.options = list(options)
        self.value = value if value in self.options else self.options[0]

    def action_cycle(self, step: int) -> None:
        i = self.options.index(self.value)
        self.value = self.options[(i + step) % len(self.options)]
        self.refresh()

    def action_submit(self) -> None:
        self.post_message(self.Submitted(self))

    def reset(self) -> None:
        self.value = self.options[0]
        self.refresh()

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.focus()
        self.action_cycle(1)

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    def render(self) -> Text:
        style = "bold #e8eaed on #3a4150" if self.has_focus else "on #242932"
        return Text(
            f" ‹ {self.value} › ", style=style, no_wrap=True, overflow="ellipsis"
        )


# ---------------------------------------------------------------------- #
class PresetGrid(Widget, can_focus=True):
    """Fleet preset grid: 1-15, auto (plus null and 0 for single choice).

    With multi=True several can be chosen and the click order is recorded (the order is the order written to the config).
    """

    COLS = 5
    CELL = 6

    BINDINGS = [
        Binding("left", "step(-1,0)", show=False),
        Binding("right", "step(1,0)", show=False),
        Binding("up", "step(0,-1)", show=False),
        Binding("down", "step(0,1)", show=False),
        Binding("space", "toggle", show=False),
        Binding("enter", "accept", show=False),
    ]

    class Accepted(Message):
        def __init__(self, source: "PresetGrid") -> None:
            super().__init__()
            self.source = source

    def __init__(
        self,
        tokens: Sequence[str],
        selected: Sequence[str],
        *,
        multi: bool,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.tokens = list(tokens)
        self.multi = multi
        self.order: list[str] = [t for t in selected if t in self.tokens]
        self.cursor = self.tokens.index(self.order[0]) if self.order else 0
        rows = -(-len(self.tokens) // self.COLS)
        self.styles.height = rows

    def action_step(self, dx: int, dy: int) -> None:
        row, col = divmod(self.cursor, self.COLS)
        row, col = row + dy, col + dx
        if col < 0 or col >= self.COLS or row < 0:
            return
        index = row * self.COLS + col
        if index < len(self.tokens):
            self.cursor = index
            self.refresh()

    def _toggle_at(self, index: int) -> None:
        token = self.tokens[index]
        if self.multi:
            if token in self.order:
                self.order.remove(token)
            else:
                self.order.append(token)
        else:
            self.order = [token]
        self.refresh()

    def action_toggle(self) -> None:
        self._toggle_at(self.cursor)

    def action_accept(self) -> None:
        if not self.multi:
            self._toggle_at(
                self.cursor
            )  # single choice: Enter selects and confirms at the same time
        self.post_message(self.Accepted(self))

    def on_click(self, event: events.Click) -> None:
        index = event.y * self.COLS + event.x // self.CELL
        if event.x // self.CELL >= self.COLS or not 0 <= index < len(self.tokens):
            return
        event.stop()
        self.focus()
        self.cursor = index
        self._toggle_at(index)

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    def render(self) -> Text:
        text = Text(no_wrap=True)
        for i, token in enumerate(self.tokens):
            if i and i % self.COLS == 0:
                text.append("\n")
            label = token
            if self.multi and token in self.order and len(self.order) > 1:
                label = f"{token}"
            cell = f" {label:^4} "
            style = "on #242932"
            if token in self.order:
                style = "bold #0f1115 on #98c379"
            if i == self.cursor and self.has_focus:
                style += " underline reverse"
            text.append(cell, style=style)
        return text


# ---------------------------------------------------------------------- #
class ActionLabel(Static, can_focus=True):
    """Small button that can be clicked or operated with the keyboard, e.g. [ OK ] [ Cancel ].

    ↓ past the end of a list jumps to this row; ← → move between buttons, Enter / Space presses, ↑ returns to the list.
    """

    BINDINGS = [
        Binding("enter,space", "press", show=False),
        Binding("left", "sibling(-1)", show=False),
        Binding("right", "sibling(1)", show=False),
        Binding("up", "back", show=False),
    ]

    class Clicked(Message):
        def __init__(self, source: "ActionLabel", command: str) -> None:
            super().__init__()
            self.source = source
            self.command = command

    def __init__(self, label: str, action: str, *, hotkey: str = "") -> None:
        text = Text(no_wrap=True)
        if hotkey:
            text.append(hotkey + " ", style="bold #e5c07b")
        text.append(label)
        super().__init__(text, classes="action-label")
        self.command = action

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.post_message(self.Clicked(self, self.command))

    def action_press(self) -> None:
        self.post_message(self.Clicked(self, self.command))

    def action_sibling(self, delta: int) -> None:
        row = [
            w
            for w in (self.parent.children if self.parent else [])
            if isinstance(w, ActionLabel)
        ]
        if self in row:
            target = row.index(self) + delta
            if 0 <= target < len(row):
                row[target].focus()

    def action_back(self) -> None:
        back = getattr(self.screen, "return_from_buttons", None)
        if back is not None:
            back()


# ---------------------------------------------------------------------- #
@dataclass
class Wheel:
    """One wheel: items are the display text, index is the currently selected item."""

    items: list[str]
    index: int = 0
    label: str = ""  # title shown above the wheel; a wheel with a title is also the start of a "group"
    span: int = 1  # how many wheels the title spans (used when one number is made of several digit wheels)
    wrap: bool = True  # whether scrolling past the end wraps to the other end
    gap: int = 1  # blank cells between this wheel and the previous one in the same row (0 between the digits of one number)
    divider: bool = False  # when gap is wide enough (>= 3) draw a divider in the middle, separating different resources / fields
    tight: bool = False  # narrow: the width is only 1 cell more than the content (for digit-by-digit wheels)
    row: int = 0  # which row (used for the recipe's 2×2 layout)
    color: str = ""  # colour of this group (title and selected row); empty string = default yellow


DEFAULT_WHEEL_COLOR = "#e5c07b"


class WheelPicker(Widget, can_focus=True):
    """Wheel picker like a phone alarm clock.

    Normal mode: ← → change wheel; ↑ ↓ scroll (↑ = previous value, ↓ = next value); Enter confirms.

    Grouped mode (``grouped=True``, for things like a recipe with "several numbers") has two levels:
      Level 1 pick a resource: ← → ↑ ↓ move between groups (and the OK / Cancel below), Enter goes into the group;
      Level 2 adjust the number: ← → move between the digits of the group, ↑ ↓ scroll, Enter confirms and returns to level 1,
                     Esc discards this group's change and returns to level 1 (the dialog calls ``leave_digits``).
    Tab / Shift+Tab: in normal mode jump to the next group; in grouped mode move in reading order at level 1.
    Mouse: clicking an item above / below scrolls to it (in grouped mode it also enters level 2); the mouse wheel scrolls the wheel under the pointer.
    Every value change sends ``Changed``, so the dialog can validate live or drive other wheels.
    """

    VISIBLE = 5  # how many rows are visible by default (the middle one is selected); can shrink to 3 when space is short

    BINDINGS = [
        Binding("left", "column(-1)", show=False),
        Binding("right", "column(1)", show=False),
        Binding("up", "scroll(-1)", show=False),
        Binding("down", "scroll(1)", show=False),
        Binding("pageup", "scroll(-5)", show=False),
        Binding("pagedown", "scroll(5)", show=False),
        Binding("tab", "group(1)", show=False),
        Binding("shift+tab", "group(-1)", show=False),
        Binding("enter", "accept", show=False),
    ]

    class Changed(Message):
        def __init__(self, source: "WheelPicker", column: int) -> None:
            super().__init__()
            self.source = source
            self.column = column

    class Accepted(Message):
        def __init__(self, source: "WheelPicker") -> None:
            super().__init__()
            self.source = source

    class Cancelled(Message):
        """In grouped mode, Enter / click on the Cancel cell."""

        def __init__(self, source: "WheelPicker") -> None:
            super().__init__()
            self.source = source

    class Leave(Message):
        """In grouped mode, level 1 is already at the far left / top and the key was pressed outward: direction = "left" / "up" (lets the dialog move focus)."""

        def __init__(self, source: "WheelPicker", direction: str) -> None:
            super().__init__()
            self.source = source
            self.direction = direction

    class LevelChanged(Message):
        """Grouped mode switched between level 1 / level 2: level = "group" / "digit"."""

        def __init__(self, source: "WheelPicker", level: str) -> None:
            super().__init__()
            self.source = source
            self.level = level

    def __init__(
        self,
        wheels: Sequence[Wheel],
        *,
        id: str | None = None,
        grouped: bool = False,
        buttons: Sequence[str] = (),
    ) -> None:
        super().__init__(id=id)
        self.wheels = list(wheels)
        self.col = 0
        self.rows_shown = self.VISIBLE
        self.grouped = grouped
        self.button_labels = list(
            buttons
        )  # the OK / Cancel cells below in grouped mode
        self.level = "group" if grouped else "digit"
        self.gpos = (0, 0)  # level-1 cursor: (which row target, which one in that row)
        self._entry: dict[
            int, int
        ] = {}  # values of the digits when entering level 2, used by Esc to restore
        self._labels = any(w.label for w in self.wheels)
        self._apply_height()

    def _extra_lines(self) -> int:
        return 2 if self.button_labels else 0  # divider + the OK / Cancel row

    def _apply_height(self) -> None:
        self.styles.height = self.height_for(self.rows_shown)

    def get_content_width(self, container, viewport) -> int:
        """Used when width: auto (side by side with the preset list)."""
        return max(cell_len(line) for line in str(self.render()).split("\n"))

    def height_for(self, visible: int) -> int:
        blocks = len(self._block_rows())
        return (
            blocks * (visible + (1 if self._labels else 0))
            + (blocks - 1)
            + self._extra_lines()
        )

    def set_visible(self, visible: int) -> None:
        """How many rows to show (odd). Shrinks to 3 rows when the terminal is too short."""
        self.rows_shown = visible
        self._apply_height()
        self.refresh()

    @property
    def in_digits(self) -> bool:
        return self.grouped and self.level == "digit"

    # ------------------------------------------------------------------ #
    def values(self) -> list[str]:
        return [w.items[w.index] for w in self.wheels]

    def set_wheel(self, column: int, items: Sequence[str], index: int) -> None:
        wheel = self.wheels[column]
        wheel.items = list(items)
        wheel.index = min(max(index, 0), len(wheel.items) - 1)
        self.refresh()

    def set_index(self, column: int, index: int) -> None:
        wheel = self.wheels[column]
        wheel.index = min(max(index, 0), len(wheel.items) - 1)
        self.refresh()

    def scroll_wheel(self, column: int, delta: int) -> None:
        wheel = self.wheels[column]
        n = len(wheel.items)
        if n <= 1 or delta == 0:
            return
        if wheel.wrap:
            wheel.index = (wheel.index + delta) % n
        else:
            new = min(max(wheel.index + delta, 0), n - 1)
            if new == wheel.index:
                return
            wheel.index = new
        self.refresh()
        self.post_message(self.Changed(self, column))

    # --- geometry: wheels are split into rows by row, each row starts at x=0 ------ #
    def _block_rows(self) -> list[list[int]]:
        rows: dict[int, list[int]] = {}
        for i, w in enumerate(self.wheels):
            rows.setdefault(w.row, []).append(i)
        return [rows[k] for k in sorted(rows)]

    def _block_height(self) -> int:
        return self.rows_shown + (1 if self._labels else 0)

    def _widths(self) -> list[int]:
        widths = []
        for w in self.wheels:
            content = max(cell_len(i) for i in w.items)
            width = content + 1 if w.tight else max(3, content + 2)
            if w.label and w.span == 1:  # the title of a single wheel must fit
                width = max(width, cell_len(w.label) + 1)
            widths.append(width)
        return widths

    def _starts(self) -> dict[int, int]:
        widths, starts = self._widths(), {}
        for members in self._block_rows():
            x = 0
            for pos, idx in enumerate(members):
                if pos:
                    x += self.wheels[idx].gap
                starts[idx] = x
                x += widths[idx]
        return starts

    def _locate(self, x: int, y: int) -> tuple[int, int]:
        """Screen coordinates → (wheel index or -1, row offset within that row: 0 = middle, -2 = top)."""
        height = self._block_height()
        block, inner = divmod(y, height + 1)
        rows = self._block_rows()
        if block >= len(rows) or inner >= height:
            return -1, 0
        widths, starts = self._widths(), self._starts()
        offset = inner - (1 if self._labels else 0) - self.rows_shown // 2
        for idx in rows[block]:
            if starts[idx] <= x < starts[idx] + widths[idx]:
                return idx, offset
        return -1, offset

    def _group_starts(self) -> list[int]:
        starts = [i for i, w in enumerate(self.wheels) if w.label]
        return starts or [0]

    def _group_of(self, column: int) -> int:
        """Start of the group this wheel belongs to (a wheel with a title)."""
        starts = [s for s in self._group_starts() if s <= column]
        return starts[-1] if starts else 0

    def _group_range(self, start: int) -> range:
        return range(
            start, min(start + max(1, self.wheels[start].span), len(self.wheels))
        )

    # --- grouped mode level 1: target cells (each group + the action cells below) --- #
    def _targets(self) -> list[list[tuple[str, Any]]]:
        """Target of each row: ("group", first wheel) or ("action", name)."""
        rows: list[list[tuple[str, Any]]] = []
        starts = set(self._group_starts())
        for members in self._block_rows():
            rows.append([("group", i) for i in members if i in starts])
        if self.button_labels:
            rows.append([("action", name) for name in self.button_labels])
        return [r for r in rows if r]

    def _current_target(self) -> tuple[str, Any]:
        rows = self._targets()
        r = min(self.gpos[0], len(rows) - 1)
        c = min(self.gpos[1], len(rows[r]) - 1)
        return rows[r][c]

    def _action_cells(self) -> list[tuple[str, int, int]]:
        cells, x = [], 0
        for name in self.button_labels:
            width = cell_len(f"[ {name} ]")
            cells.append((name, x, x + width))
            x += width + 2
        return cells

    def _action_line(self) -> int:
        return self.height_for(self.rows_shown) - 1

    # --- actions ----------------------------------------------------------- #
    def _move_target(self, dr: int, dc: int) -> None:
        rows = self._targets()
        r, c = self.gpos
        if dr:
            nr = min(max(r + dr, 0), len(rows) - 1)
            nc = min(c, len(rows[nr]) - 1)
        else:
            nr, nc = r, min(max(c + dc, 0), len(rows[r]) - 1)
        self.gpos = (nr, nc)
        self.refresh()

    def enter_digits(self, start: int, column: int | None = None) -> None:
        """Grouped mode: enter level 2 and adjust this group's digits. Remembers the current values so Esc can restore them."""
        self.level = "digit"
        group = self._group_range(start)
        self.col = column if column is not None and column in group else start
        self._entry = {i: self.wheels[i].index for i in group}
        self.refresh()
        self.post_message(self.LevelChanged(self, "digit"))

    def leave_digits(self, *, revert: bool) -> None:
        """Return to level 1. With revert=True restore this group's values from before entering (Esc)."""
        if not self.in_digits:
            return
        start = self._group_of(self.col)
        if revert:
            for i, index in self._entry.items():
                self.wheels[i].index = index
            self.post_message(self.Changed(self, start))
        self.level = "group"
        self._entry = {}
        self.refresh()
        self.post_message(self.LevelChanged(self, "group"))

    def action_column(self, direction: int) -> None:
        if self.grouped and self.level == "group":
            if direction < 0 and self.gpos[1] == 0:
                self.post_message(self.Leave(self, "left"))
                return
            self._move_target(0, direction)
            return
        new = self.col + direction
        if self.in_digits and new not in self._group_range(self._group_of(self.col)):
            return  # level 2 only moves between this group's digits
        if 0 <= new < len(self.wheels):
            self.col = new
            self.refresh()

    def action_scroll(self, delta: int) -> None:
        if self.grouped and self.level == "group":
            if abs(delta) == 1:  # level 1: ↑ ↓ change row
                if delta < 0 and self.gpos[0] == 0:
                    self.post_message(self.Leave(self, "up"))
                    return
                self._move_target(delta, 0)
            return
        self.scroll_wheel(self.col, delta)

    def action_group(self, direction: int) -> None:
        if self.grouped:
            if self.level == "group":  # walk through all targets in reading order
                flat = [
                    (r, c)
                    for r, row in enumerate(self._targets())
                    for c in range(len(row))
                ]
                at = (
                    flat.index(
                        (min(self.gpos[0], len(self._targets()) - 1), self.gpos[1])
                    )
                    if self.gpos in flat
                    else 0
                )
                self.gpos = flat[min(max(at + direction, 0), len(flat) - 1)]
                self.refresh()
            return
        starts = self._group_starts()
        current = max((i for i, s in enumerate(starts) if s <= self.col), default=0)
        new = min(max(current + direction, 0), len(starts) - 1)
        self.col = starts[new]
        self.refresh()

    def action_accept(self) -> None:
        if not self.grouped:
            self.post_message(self.Accepted(self))
        elif self.level == "digit":
            self.leave_digits(revert=False)  # confirm this group and return to level 1
        else:
            kind, value = self._current_target()
            if kind == "group":
                self.enter_digits(value)
            elif value == self.button_labels[0]:
                self.post_message(self.Accepted(self))
            else:
                self.post_message(self.Cancelled(self))

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.focus()
        if self.button_labels and event.y == self._action_line():
            for i, (name, x0, x1) in enumerate(self._action_cells()):
                if x0 <= event.x < x1:
                    self.gpos = (len(self._targets()) - 1, i)
                    self.refresh()
                    self.post_message(
                        self.Accepted(self) if i == 0 else self.Cancelled(self)
                    )
            return
        column, offset = self._locate(event.x, event.y)
        if column < 0:
            return
        if self.grouped:
            start = self._group_of(column)
            if self.in_digits and self._group_of(self.col) != start:
                self.leave_digits(revert=False)
            if self.level == "group":
                self._set_gpos_for(start)
                self.enter_digits(start, column)
            else:
                self.col = column
        else:
            self.col = column
        self.refresh()
        if offset:
            self.scroll_wheel(column, offset)

    def _set_gpos_for(self, start: int) -> None:
        for r, row in enumerate(self._targets()):
            for c, (kind, value) in enumerate(row):
                if kind == "group" and value == start:
                    self.gpos = (r, c)

    def _wheel_event(self, event: events.MouseEvent, delta: int) -> None:
        event.stop()
        event.prevent_default()
        column, _ = self._locate(event.x, event.y)
        if column >= 0:
            if self.grouped and not (
                self.in_digits and self._group_of(self.col) == self._group_of(column)
            ):
                return  # in grouped mode you must enter the group before you can scroll
            self.col = column
            self.scroll_wheel(column, delta)

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self._wheel_event(event, -1)

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self._wheel_event(event, 1)

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    # --- drawing ----------------------------------------------------------- #
    DIVIDER_STYLE = "#4b5263"

    @staticmethod
    def _gap_text(wheel: Wheel) -> str:
        g = wheel.gap
        if wheel.divider and g >= 3:
            left = (g - 1) // 2
            return " " * left + "│" + " " * (g - 1 - left)
        return " " * g

    def _focus_group(self) -> int | None:
        """In grouped mode, the group the cursor is on (None when the cursor is on an action cell)."""
        if not self.grouped:
            return None
        kind, value = self._current_target()
        if self.level == "digit":
            return self._group_of(self.col)
        return value if kind == "group" else None

    def _label_line(
        self, members: list[int], widths: list[int], starts: dict[int, int]
    ) -> list[tuple[str, str]]:
        """Title row: (text, style) segments. A title spans all wheels of its group, with dividers drawn between groups."""
        out: list[tuple[str, str]] = []
        x = 0
        focus_group = self._focus_group()
        for k, idx in enumerate(members):
            w = self.wheels[idx]
            start = starts[idx]
            if start < x:  # already covered by the previous title
                continue
            if start > x:
                gap = start - x
                divider = k and w.divider and w.gap >= 3
                out.append(
                    (
                        self._gap_text(w) if divider else " " * gap,
                        self.DIVIDER_STYLE if divider else "",
                    )
                )
                x = start
            if w.label:
                last = members[min(k + w.span, len(members)) - 1]
                end = starts[last] + widths[last]
                style = f"bold {w.color}" if w.color else "#6b7280"
                if idx == focus_group and self.has_focus:
                    style += " reverse"
                out.append((w.label[: end - start].center(end - start), style))
                x = end
            else:
                out.append((" " * widths[idx], ""))
                x = start + widths[idx]
        return out

    def _cell_style(self, idx: int, wheel: Wheel) -> str:
        """Style of the middle row (the selected value)."""
        tint = wheel.color or DEFAULT_WHEEL_COLOR
        base = f"bold {wheel.color or '#e8eaed'}"
        if self.grouped:
            group = self._group_range(self._group_of(idx))
            focus = self._focus_group()
            in_focus = focus is not None and idx in self._group_range(focus)
            if self.level == "group":
                if in_focus:  # level 1: the whole group lights up
                    return (
                        f"bold #0f1115 on {tint}"
                        if self.has_focus
                        else f"{base} on #3a4150"
                    )
                return f"{base} on #242932"
            if in_focus:  # level 2: this group is dimly lit, the digit being adjusted is brightest
                if idx == self.col:
                    return (
                        f"bold #0f1115 on {tint}"
                        if self.has_focus
                        else f"{base} on #3a4150"
                    )
                return f"{base} on #3a4150"
            return f"{base} on #242932"
        if idx == self.col:
            return f"bold #0f1115 on {tint}" if self.has_focus else f"{base} on #3a4150"
        return f"{base} on #242932"

    def render(self) -> Text:
        widths, starts = self._widths(), self._starts()
        half = self.rows_shown // 2
        text = Text(no_wrap=True)
        rows = self._block_rows()
        extent = max((starts[i] + widths[i] for i in starts), default=1)
        if self.button_labels:
            extent = max(extent, self._action_cells()[-1][2])

        for b, members in enumerate(rows):
            if b:
                text.append("\n")  # finish the last row of the previous line
                text.append(
                    "─" * extent, style=self.DIVIDER_STYLE
                )  # divider between rows
                text.append("\n")
            if self._labels:
                for piece, style in self._label_line(members, widths, starts):
                    text.append(piece, style=style)
                text.append("\n")
            for r in range(-half, half + 1):
                for k, idx in enumerate(members):
                    wheel = self.wheels[idx]
                    if k and wheel.gap:
                        if wheel.divider and wheel.gap >= 3:
                            text.append(self._gap_text(wheel), style=self.DIVIDER_STYLE)
                        else:
                            text.append(
                                " " * wheel.gap, style="on #242932" if r == 0 else ""
                            )
                    n = len(wheel.items)
                    at = wheel.index + r
                    if wheel.wrap and n:
                        at %= n
                    shown = wheel.items[at] if 0 <= at < n else ""
                    cell = shown.center(widths[idx])
                    if r == 0:
                        style = self._cell_style(idx, wheel)
                    elif abs(r) == 1:
                        style = "#9aa0a6"
                    else:
                        style = "#4b5263"
                    text.append(cell, style=style)
                if r < half:
                    text.append("\n")
        if self.button_labels:
            text.append("\n")
            text.append("─" * extent, style=self.DIVIDER_STYLE)
            text.append("\n")
            kind, value = (
                self._current_target() if self.level == "group" else ("", None)
            )
            for name, x0, x1 in self._action_cells():
                chosen = kind == "action" and value == name
                style = (
                    "bold #0f1115 on #e5c07b"
                    if chosen and self.has_focus
                    else "bold #e8eaed on #3a4150"
                    if chosen
                    else "bold #e8eaed on #242932"
                )
                text.append(f"[ {name} ]", style=style)
                text.append("  ")
        return text
