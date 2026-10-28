"""編輯器用的小元件:清單、循環選單、preset 格子、可點擊的按鈕標籤。

全部自己畫(render)而不依賴 Textual 內建的 OptionList / Button / Select,
這樣外觀一致,也不受各版本 API 差異影響。
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
    gap: int = 1                # 與同一排前一個滾輪之間空幾格(同一個數字的位數之間用 0)
    divider: bool = False       # gap 夠寬(>= 3)時在中間畫一條分隔線,分開不同的資源 / 欄位
    tight: bool = False         # 窄版:寬度只比內容多 1 格(逐位數滾輪用)
    row: int = 0                # 第幾排(配方用 2×2 排版)
    color: str = ""             # 該組的顏色(標題與選中列);空字串 = 預設黃色


DEFAULT_WHEEL_COLOR = "#e5c07b"


class WheelPicker(Widget, can_focus=True):
    """像手機鬧鐘的滾輪選擇器。

    一般模式:← → 換滾輪;↑ ↓ 滾動(↑ = 上一個值,↓ = 下一個值);Enter 確定。

    分組模式(``grouped=True``,配方這類「好幾個數字」用)分兩層:
      第一層 選資源:← → ↑ ↓ 在各組(與下方的 OK / Cancel)之間移動,Enter 進入該組;
      第二層 調數字:← → 在該組的位數間移動,↑ ↓ 滾動,Enter 確定並回到第一層,
                     Esc 放棄這一組的修改並回到第一層(由對話框呼叫 ``leave_digits``)。
    Tab / Shift+Tab:一般模式跳到下一組;分組模式在第一層依閱讀順序移動。
    滑鼠:點上/下方的項目會滾到那一項(分組模式會同時進入第二層);滑鼠滾輪滾動所在的滾輪。
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

    class Cancelled(Message):
        """分組模式下在 Cancel 格按 Enter / 點擊。"""

        def __init__(self, source: "WheelPicker") -> None:
            super().__init__()
            self.source = source

    class LevelChanged(Message):
        """分組模式切換第一層 / 第二層:level = "group" / "digit"。"""

        def __init__(self, source: "WheelPicker", level: str) -> None:
            super().__init__()
            self.source = source
            self.level = level

    def __init__(self, wheels: Sequence[Wheel], *, id: str | None = None,
                 grouped: bool = False, buttons: Sequence[str] = ()) -> None:
        super().__init__(id=id)
        self.wheels = list(wheels)
        self.col = 0
        self.rows_shown = self.VISIBLE
        self.grouped = grouped
        self.button_labels = list(buttons)         # 分組模式下方的 OK / Cancel 格
        self.level = "group" if grouped else "digit"
        self.gpos = (0, 0)                   # 第一層游標:(第幾列目標, 該列第幾個)
        self._entry: dict[int, int] = {}     # 進入第二層時各位數的值,Esc 用來還原
        self._labels = any(w.label for w in self.wheels)
        self._apply_height()

    def _extra_lines(self) -> int:
        return 2 if self.button_labels else 0       # 分隔線 + OK / Cancel 那一列

    def _apply_height(self) -> None:
        self.styles.height = self.height_for(self.rows_shown)

    def height_for(self, visible: int) -> int:
        blocks = len(self._block_rows())
        return (blocks * (visible + (1 if self._labels else 0)) + (blocks - 1)
                + self._extra_lines())

    def set_visible(self, visible: int) -> None:
        """顯示幾列(奇數)。終端機太矮時縮成 3 列。"""
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
            content = max(cell_len(i) for i in w.items)
            width = content + 1 if w.tight else max(3, content + 2)
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
                    x += self.wheels[idx].gap
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

    def _group_of(self, column: int) -> int:
        """該滾輪所屬那一組的起點(有標題的滾輪)。"""
        starts = [s for s in self._group_starts() if s <= column]
        return starts[-1] if starts else 0

    def _group_range(self, start: int) -> range:
        return range(start, min(start + max(1, self.wheels[start].span), len(self.wheels)))

    # --- 分組模式第一層:目標格(各組 + 下方的動作格)-------------------------- #
    def _targets(self) -> list[list[tuple[str, Any]]]:
        """每一列的目標:("group", 起點滾輪) 或 ("action", 名稱)。"""
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

    # --- 動作 ----------------------------------------------------------- #
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
        """分組模式:進入第二層,調整該組的位數。記下目前的值,Esc 時還原。"""
        self.level = "digit"
        group = self._group_range(start)
        self.col = column if column is not None and column in group else start
        self._entry = {i: self.wheels[i].index for i in group}
        self.refresh()
        self.post_message(self.LevelChanged(self, "digit"))

    def leave_digits(self, *, revert: bool) -> None:
        """回到第一層。revert=True 時還原這一組進入前的值(Esc)。"""
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
            self._move_target(0, direction)
            return
        new = self.col + direction
        if self.in_digits and new not in self._group_range(self._group_of(self.col)):
            return                                   # 第二層只在這一組的位數間移動
        if 0 <= new < len(self.wheels):
            self.col = new
            self.refresh()

    def action_scroll(self, delta: int) -> None:
        if self.grouped and self.level == "group":
            if abs(delta) == 1:                      # 第一層:↑ ↓ 換列
                self._move_target(delta, 0)
            return
        self.scroll_wheel(self.col, delta)

    def action_group(self, direction: int) -> None:
        if self.grouped:
            if self.level == "group":                # 依閱讀順序走過所有目標
                flat = [(r, c) for r, row in enumerate(self._targets()) for c in range(len(row))]
                at = flat.index((min(self.gpos[0], len(self._targets()) - 1),
                                 self.gpos[1])) if self.gpos in flat else 0
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
            self.leave_digits(revert=False)           # 確定這一組,回到第一層
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
                    self.post_message(self.Accepted(self) if i == 0 else self.Cancelled(self))
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
            if self.grouped and not (self.in_digits and
                                     self._group_of(self.col) == self._group_of(column)):
                return                               # 分組模式要先進入該組才能滾動
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
    DIVIDER_STYLE = "#4b5263"

    @staticmethod
    def _gap_text(wheel: Wheel) -> str:
        g = wheel.gap
        if wheel.divider and g >= 3:
            left = (g - 1) // 2
            return " " * left + "│" + " " * (g - 1 - left)
        return " " * g

    def _focus_group(self) -> int | None:
        """分組模式下,目前被游標選中的那一組(游標在動作格時為 None)。"""
        if not self.grouped:
            return None
        kind, value = self._current_target()
        if self.level == "digit":
            return self._group_of(self.col)
        return value if kind == "group" else None

    def _label_line(self, members: list[int], widths: list[int],
                    starts: dict[int, int]) -> list[tuple[str, str]]:
        """標題列:(文字, 樣式)片段。標題橫跨它的整組滾輪,組與組之間畫分隔線。"""
        out: list[tuple[str, str]] = []
        x = 0
        focus_group = self._focus_group()
        for k, idx in enumerate(members):
            w = self.wheels[idx]
            start = starts[idx]
            if start < x:                               # 已被前一個標題涵蓋
                continue
            if start > x:
                gap = start - x
                divider = k and w.divider and w.gap >= 3
                out.append((self._gap_text(w) if divider else " " * gap,
                            self.DIVIDER_STYLE if divider else ""))
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
        """中間那一列(選中的值)的樣式。"""
        tint = wheel.color or DEFAULT_WHEEL_COLOR
        base = f"bold {wheel.color or '#e8eaed'}"
        if self.grouped:
            group = self._group_range(self._group_of(idx))
            focus = self._focus_group()
            in_focus = focus is not None and idx in self._group_range(focus)
            if self.level == "group":
                if in_focus:                              # 第一層:整組亮起
                    return f"bold #0f1115 on {tint}" if self.has_focus else f"{base} on #3a4150"
                return f"{base} on #242932"
            if in_focus:                                  # 第二層:這一組暗亮,正在調的那位最亮
                if idx == self.col:
                    return f"bold #0f1115 on {tint}" if self.has_focus else f"{base} on #3a4150"
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
                text.append("\n")                      # 結束上一排的最後一列
                text.append("─" * extent, style=self.DIVIDER_STYLE)     # 排與排之間的分隔線
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
                            text.append(" " * wheel.gap,
                                        style="on #242932" if r == 0 else "")
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
            kind, value = self._current_target() if self.level == "group" else ("", None)
            for name, x0, x1 in self._action_cells():
                chosen = kind == "action" and value == name
                style = ("bold #0f1115 on #e5c07b" if chosen and self.has_focus
                         else "bold #e8eaed on #3a4150" if chosen else "bold #e8eaed on #242932")
                text.append(f"[ {name} ]", style=style)
                text.append("  ")
        return text
