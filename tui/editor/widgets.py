"""編輯器用的小元件:清單、循環選單、preset 格子、可點擊的按鈕標籤。

全部自己畫(render)而不依賴 Textual 內建的 OptionList / Button / Select,
這樣外觀一致,也不受各版本 API 差異影響。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

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
    checked: Optional[bool] = None     # None:不畫勾選框
    toggle: bool = False               # 點擊/空白鍵是「切換」而不是「選取」
    style: str = ""


class PickList(Widget, can_focus=True):
    """可捲動的單欄清單。上下鍵移動;Enter 選取;空白鍵切換勾選。"""

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
        """游標移到另一項(用來即時更新路徑列、預覽等)。"""

        def __init__(self, source: "PickList", index: int) -> None:
            super().__init__()
            self.source = source
            self.index = index

    class Edge(Message):
        """已在最上/最下一項時又往外按:direction = -1 / +1。"""

        def __init__(self, source: "PickList", direction: int) -> None:
            super().__init__()
            self.source = source
            self.direction = direction

    def __init__(self, rows: Sequence[Row] = (), *, max_visible: int = 10,
                 empty: str = "(empty)", id: str | None = None) -> None:
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
        """往 delta 方向移動 |delta| 個可選項;回傳是否有動。"""
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
                line.append("[x] " if row.checked else "[ ] ",
                            style=GREEN if row.checked else DIM)
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
    """用 ←/→ 或空白鍵在固定選項間循環的輸入格。Enter 送出。"""

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

    def __init__(self, options: Sequence[str], *, value: str | None = None,
                 id: str | None = None) -> None:
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
        return Text(f" ‹ {self.value} › ", style=style, no_wrap=True, overflow="ellipsis")


# ---------------------------------------------------------------------- #
class PresetGrid(Widget, can_focus=True):
    """艦隊 preset 的格子:1~15、auto(單選時另有 null、0)。

    multi=True 時可複選,並記錄點選順序(順序就是寫進設定檔的順序)。
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

    def __init__(self, tokens: Sequence[str], selected: Sequence[str], *,
                 multi: bool, id: str | None = None) -> None:
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
            self._toggle_at(self.cursor)       # 單選:Enter 同時選取並確定
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
class ActionLabel(Static):
    """可點擊的小按鈕,例如 [ OK ] [ Cancel ]。"""

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


# ---------------------------------------------------------------------- #
@dataclass
class Wheel:
    """一個滾輪:items 為顯示文字,index 為目前選中的項目。"""
    items: list[str]
    index: int = 0
    label: str = ""             # 顯示在滾輪上方的標題;有標題的滾輪同時是「一組」的起點
    span: int = 1               # 標題橫跨幾個滾輪(一個數字由多位數滾輪組成時使用)
    wrap: bool = True           # 滾到盡頭是否繞回另一端
    gap_before: bool = False    # 與同一排前一個滾輪之間多留一點空隙(分組用)
    row: int = 0                # 第幾排(配方用 2×2 排版)
    color: str = ""             # 該組的顏色(標題與選中列);空字串 = 預設黃色


DEFAULT_WHEEL_COLOR = "#e5c07b"


class WheelPicker(Widget, can_focus=True):
    """像手機鬧鐘的滾輪選擇器。

    ← → 換滾輪;↑ ↓ 滾動(↑ = 上一個值,↓ = 下一個值,與畫面上項目由上到下的排列一致);
    Tab / Shift+Tab 跳到下一組 / 上一組;Enter 確定。
    滑鼠:點上/下方的項目會滾到那一項;滑鼠滾輪(往上 = 上一個)滾動所在的滾輪。
    每次數值變動送出 ``Changed``,對話框可據此即時驗證或連動其他滾輪。
    """

    VISIBLE = 5          # 預設一次看到幾列(中間那列是選中的);空間不足時可縮成 3

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

    def __init__(self, wheels: Sequence[Wheel], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.wheels = list(wheels)
        self.col = 0
        self.rows_shown = self.VISIBLE
        self._labels = any(w.label for w in self.wheels)
        self._apply_height()

    def _apply_height(self) -> None:
        blocks = len(self._block_rows())
        self.styles.height = blocks * self._block_height() + (blocks - 1)

    def height_for(self, visible: int) -> int:
        blocks = len(self._block_rows())
        return blocks * (visible + (1 if self._labels else 0)) + (blocks - 1)

    def set_visible(self, visible: int) -> None:
        """顯示幾列(奇數)。終端機太矮時縮成 3 列。"""
        self.rows_shown = visible
        self._apply_height()
        self.refresh()

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

    # --- 幾何:滾輪依 row 分成幾排,每排各自從 x=0 開始 ---------------------- #
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
            width = max(3, max(cell_len(i) for i in w.items) + 2)
            if w.label and w.span == 1:              # 單一滾輪的標題要放得下
                width = max(width, cell_len(w.label) + 1)
            widths.append(width)
        return widths

    def _starts(self) -> dict[int, int]:
        widths, starts = self._widths(), {}
        for members in self._block_rows():
            x = 0
            for pos, idx in enumerate(members):
                if pos:
                    x += 2 if self.wheels[idx].gap_before else 1
                starts[idx] = x
                x += widths[idx]
        return starts

    def _locate(self, x: int, y: int) -> tuple[int, int]:
        """畫面座標 → (滾輪索引或 -1, 該排內的列位移:0=中間、-2=最上)。"""
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

    # --- 動作 ----------------------------------------------------------- #
    def action_column(self, direction: int) -> None:
        new = self.col + direction
        if 0 <= new < len(self.wheels):
            self.col = new
            self.refresh()

    def action_scroll(self, delta: int) -> None:
        self.scroll_wheel(self.col, delta)

    def action_group(self, direction: int) -> None:
        starts = self._group_starts()
        current = max((i for i, s in enumerate(starts) if s <= self.col), default=0)
        new = min(max(current + direction, 0), len(starts) - 1)
        self.col = starts[new]
        self.refresh()

    def action_accept(self) -> None:
        self.post_message(self.Accepted(self))

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.focus()
        column, offset = self._locate(event.x, event.y)
        if column < 0:
            return
        self.col = column
        self.refresh()
        if offset:
            self.scroll_wheel(column, offset)

    def _wheel_event(self, event: events.MouseEvent, delta: int) -> None:
        event.stop()
        event.prevent_default()
        column, _ = self._locate(event.x, event.y)
        if column >= 0:
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

    # --- 繪製 ----------------------------------------------------------- #
    def render(self) -> Text:
        widths, starts = self._widths(), self._starts()
        half = self.rows_shown // 2
        text = Text(no_wrap=True)
        rows = self._block_rows()

        for b, members in enumerate(rows):
            if b:
                text.append("\n\n")                 # 結束上一排的最後一列,再空一行
            if self._labels:
                pos = 0
                for k, idx in enumerate(members):
                    w = self.wheels[idx]
                    if not w.label:
                        continue
                    last = members[min(k + w.span, len(members)) - 1]
                    start, end = starts[idx], starts[last] + widths[last]
                    text.append(" " * max(0, start - pos))
                    text.append(w.label[: end - start].center(end - start),
                                style=f"bold {w.color}" if w.color else "#6b7280")
                    pos = end
                text.append("\n")
            for r in range(-half, half + 1):
                for k, idx in enumerate(members):
                    wheel = self.wheels[idx]
                    if k:
                        text.append(" " * (2 if wheel.gap_before else 1),
                                    style="on #242932" if r == 0 else "")
                    n = len(wheel.items)
                    at = wheel.index + r
                    if wheel.wrap and n:
                        at %= n
                    shown = wheel.items[at] if 0 <= at < n else ""
                    cell = shown.center(widths[idx])
                    if r == 0:
                        active = idx == self.col
                        tint = wheel.color or DEFAULT_WHEEL_COLOR
                        if active and self.has_focus:
                            style = f"bold #0f1115 on {tint}"
                        elif active:
                            style = f"bold {wheel.color or '#e8eaed'} on #3a4150"
                        else:
                            style = f"bold {wheel.color or '#e8eaed'} on #242932"
                    elif abs(r) == 1:
                        style = "#9aa0a6"
                    else:
                        style = "#4b5263"
                    text.append(cell, style=style)
                if r < half:
                    text.append("\n")
        return text
