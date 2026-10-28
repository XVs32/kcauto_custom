"""編輯器的對話框(ModalScreen)。

共同約定
  * 取消(Esc / 點 Cancel)→ dismiss(None);確定 → dismiss(Picked(value))。
    用 ``Picked`` 包起來,因為 ``None`` 本身(null)也是合法的欄位值。
  * 在輸入框內按 Enter:有內容 = 新增/確認該筆;空白 = 按下 OK。
  * 方向鍵:在輸入框按 ↓ 進入清單,在清單最上方按 ↑ 回到輸入框。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import partial
from typing import Any, Callable, Optional, Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

try:                                    # TextArea 需要較新的 Textual;沒有就退回單行輸入
    from textual.widgets import TextArea
except ImportError:                     # pragma: no cover
    TextArea = None

from ..schema import Field, Kind
from . import model as M
from . import narrow as N
from . import tree as TR
from .widgets import ActionLabel, CycleBox, PickList, PresetGrid, Row, Wheel, WheelPicker

ERR = "bold #e06c75"
DIM = "#6b7280"


@dataclass(frozen=True)
class Picked:
    value: Any


def _static(text: str | Text, *, classes: str = "", id: str | None = None) -> Static:
    return Static(text if isinstance(text, Text) else Text(text), classes=classes, id=id)


class Dialog(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    # 清單元件 id → (清單以外的元件佔用的列數, 預設最多顯示幾列)。
    # 終端機太矮時依視窗高度縮短清單,讓底部的 OK / Cancel 不會被切掉。
    FIT: dict[str, tuple[int, int]] = {}

    def on_resize(self, event) -> None:
        self.set_class(event.size.width < N.DIALOG_NARROW, "narrow")
        for widget_id, (overhead, base) in self.FIT.items():
            try:
                lst = self.query_one(f"#{widget_id}", PickList)
            except Exception:
                continue
            lst.max_visible = max(3, min(base, event.size.height - overhead))
            lst.set_rows(lst.rows)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def accept(self, value: Any) -> None:
        self.dismiss(Picked(value))

    def run_command(self, command: str) -> None:        # 子類別覆寫
        if command == "cancel":
            self.action_cancel()

    def on_action_label_clicked(self, event: ActionLabel.Clicked) -> None:
        event.stop()
        self.run_command(event.command)

    def show_error(self, message: str = "") -> None:
        self.query_one("#err", Static).update(Text(message, style=ERR))

    def header(self, title: str, help_text: str = "") -> ComposeResult:
        yield _static(title, classes="dlg-title")
        if help_text:
            yield _static(help_text, classes="dlg-help")

    @staticmethod
    def buttons(*items: tuple[str, str]) -> Horizontal:
        return Horizontal(*(ActionLabel(label, cmd) for label, cmd in items),
                          classes="dlg-buttons")


# ---------------------------------------------------------------------- #
class ChoiceDialog(Dialog):
    """單選清單(enum)。"""

    FIT = {"choices": (11, 12)}

    def __init__(self, title: str, help_text: str,
                 options: Sequence[tuple[str, Any]], current: Any) -> None:
        super().__init__()
        self.title_text, self.help_text = title, help_text
        self.options = list(options)
        self.current = current

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg"):
            yield from self.header(self.title_text, self.help_text)
            rows, cursor = [], 0
            for i, (label, value) in enumerate(self.options):
                is_now = value == self.current and type(value) is type(self.current)
                if is_now:
                    cursor = i
                rows.append(Row(("● " if is_now else "  ") + label))
            lst = PickList(rows, max_visible=12, id="choices")
            lst.cursor = cursor
            yield lst
            yield self.buttons(("Cancel", "cancel"))

    def on_mount(self) -> None:
        self.query_one(PickList).focus()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        self.accept(self.options[event.index][1])


# ---------------------------------------------------------------------- #
class TextDialog(Dialog):
    """int / int|str / str 的單行輸入。整數可用 ↑↓ 微調。"""

    BINDINGS = [
        *Dialog.BINDINGS,
        Binding("up", "step(1)", show=False),
        Binding("down", "step(-1)", show=False),
    ]

    def __init__(self, field: Field, current: Any) -> None:
        super().__init__()
        self.field = field
        self.current = current

    def compose(self) -> ComposeResult:
        f = self.field
        with Vertical(classes="dlg"):
            yield from self.header(f.label, f.help)
            yield _static(f"{f.key}   {M.type_label(f)}   default {M.format_value(f, f.default, 30)}",
                          classes="dlg-meta")
            yield Input(value="" if self.current is None else str(self.current), id="value")
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def _parse(self, text: str) -> tuple[Any, str]:
        try:
            value = M.parse_input(self.field, text)
        except M.ParseError as exc:
            return None, str(exc)
        return value, M.check_value(self.field, value) or ""

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        _, error = self._parse(event.value)
        self.show_error(error if event.value.strip() else "")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._submit()

    def _submit(self) -> None:
        value, error = self._parse(self.query_one(Input).value)
        if error:
            self.show_error(error)
            return
        self.accept(value)

    def action_step(self, delta: int) -> None:
        if self.field.kind is not Kind.INT:
            return
        box = self.query_one(Input)
        value, error = self._parse(box.value)
        if error and not isinstance(value, int):
            new = self.field.min if self.field.min is not None else 0
        else:
            new = M.step_int(self.field, value, delta)
            if new is None:
                return
        box.value = str(new)
        box.cursor_position = len(box.value)

    def run_command(self, command: str) -> None:
        if command == "ok":
            self._submit()
        else:
            super().run_command(command)


# ---------------------------------------------------------------------- #
class ListDialog(Dialog):
    """字串/整數陣列(chip 清單)。輸入框可一次貼上多個項目(以逗號或空白分隔)。"""

    FIT = {"items": (17, 8)}

    def __init__(self, field: Field, items: Sequence[Any]) -> None:
        super().__init__()
        self.field = field
        self.items: list[Any] = list(items)
        self._editing: Optional[int] = None

    def compose(self) -> ComposeResult:
        f = self.field
        with Vertical(classes="dlg"):
            yield from self.header(f.label, f.help)
            if f.pattern_hint:
                yield _static(f"format: {f.pattern_hint}", classes="dlg-meta")
            if f.lengths:
                yield _static("count must be " + " or ".join(str(n) for n in f.lengths),
                              classes="dlg-meta")
            yield PickList(self._build_rows(), max_visible=8, id="items")
            yield Input(placeholder="type an item, Enter to add — empty Enter = OK", id="add")
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("OK", "ok"), ("Remove", "remove"), ("Cancel", "cancel"))

    def _build_rows(self) -> list[Row]:
        return [Row(f"{i + 1:>2}. {item}") for i, item in enumerate(self.items)]

    def _refresh_rows(self, cursor: int | None = None) -> None:
        self.query_one("#items", PickList).set_rows(self._build_rows(), cursor)

    def on_mount(self) -> None:
        self.query_one("#add", Input).focus()

    # --- 輸入 -------------------------------------------------------------- #
    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        text = event.value.strip()
        if not text:
            if self._editing is not None:        # 編輯到一半清空 = 放棄這次編輯
                self._editing = None
                self.show_error()
                return
            self._finish()
            return
        tokens = [t for t in re.split(r"[,\s]+", text) if t]
        base = [x for i, x in enumerate(self.items) if i != self._editing]
        staged = list(base)
        for token in tokens:
            candidate = M.coerce_like(staged, token)
            error = M.list_item_error(self.field, staged, candidate)
            if error:
                self.show_error(error)
                return
            staged.append(candidate)
        added = staged[len(base):]
        if self._editing is None:
            self.items.extend(added)
            cursor = len(self.items) - 1
        else:
            at = self._editing
            self.items[at:at + 1] = added
            cursor = at
            self._editing = None
        event.input.value = ""
        self.show_error()
        self._refresh_rows(cursor)

    def _finish(self) -> None:
        errors = self.field.validate(self.items)
        if errors:
            self.show_error(errors[0])
            return
        self.accept(list(self.items))

    # --- 清單 -------------------------------------------------------------- #
    def action_focus_list(self) -> None:
        if self.items and isinstance(self.focused, (Input,)):
            self.query_one("#items", PickList).focus()

    BINDINGS = [
        *Dialog.BINDINGS,
        Binding("down", "focus_list", show=False),
        Binding("delete,backspace,x", "remove", show=False),
    ]

    def on_pick_list_edge(self, event: PickList.Edge) -> None:
        event.stop()
        if event.direction < 0:
            self.query_one("#add", Input).focus()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        """Enter:把該項放回輸入框修改。"""
        event.stop()
        self._editing = event.index
        box = self.query_one("#add", Input)
        box.value = str(self.items[event.index])
        box.cursor_position = len(box.value)
        box.focus()

    def action_remove(self) -> None:
        lst = self.query_one("#items", PickList)
        if self.focused is not lst or not self.items:
            return
        del self.items[lst.cursor]
        self._editing = None
        self._refresh_rows(lst.cursor)
        if not self.items:
            self.query_one("#add", Input).focus()

    def run_command(self, command: str) -> None:
        if command == "ok":
            self._finish()
        elif command == "remove":
            lst = self.query_one("#items", PickList)
            if self.items:
                del self.items[lst.cursor]
                self._editing = None
                self._refresh_rows(lst.cursor)
        else:
            super().run_command(command)


# ---------------------------------------------------------------------- #
class TableDialog(Dialog):
    """多欄表格:每列是以分隔字元串起來的一個字串(A>B、A:line_ahead、排程規則…)。"""

    FIT = {"rows": (18, 8)}

    def __init__(self, field: Field, items: Sequence[Any]) -> None:
        super().__init__()
        self.field = field
        self.spec = M.TABLES[field.key]
        self.items: list[Any] = list(items)
        self._editing: Optional[int] = None

    BINDINGS = [
        *Dialog.BINDINGS,
        Binding("down", "focus_rows", show=False),
        Binding("delete,backspace,x", "remove", show=False),
    ]

    # --- 畫面 -------------------------------------------------------------- #
    def compose(self) -> ComposeResult:
        f, spec = self.field, self.spec
        with Vertical(classes="dlg dlg-wide"):
            yield from self.header(f.label, f.help)
            if spec.note:
                yield _static(spec.note, classes="dlg-meta")
            yield _static(self._header_line(), classes="dlg-colhead")
            yield PickList(self._build_rows(), max_visible=8, id="rows")
            with Horizontal(id="cells"):
                for i, col in enumerate(spec.columns):
                    if col.choices:
                        yield CycleBox(col.choices, id=f"cell-{i}")
                    else:
                        yield Input(placeholder=col.name + ("?" if col.optional else ""),
                                    id=f"cell-{i}")
            yield _static(self._suggestions(), classes="dlg-meta", id="suggest")
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("OK", "ok"), ("Remove", "remove"), ("Cancel", "cancel"))

    def _header_line(self) -> str:
        return "    " + " │ ".join(M.pad_cells(c.name, c.width) for c in self.spec.columns)

    def _build_rows(self) -> list[Row]:
        rows = []
        for i, item in enumerate(self.items):
            cells = self.spec.parse(item)
            body = " │ ".join(M.pad_cells(c, col.width)
                             for c, col in zip(cells, self.spec.columns))
            rows.append(Row(f"{i + 1:>2}. {body}"))
        return rows

    def _suggestions(self) -> str:
        if self.field.key != "scheduler.rules":
            return ""
        seen = M.table_suggestions(self.items, self.spec)
        examples = [["time", "sorties_run"], [], ["stop"], ["kcauto", "combat"], []]
        parts = []
        for col, have, ex in zip(self.spec.columns, seen, examples):
            names = list(dict.fromkeys(have + ex))[:5]
            if names:
                parts.append(f"{col.name}: {', '.join(names)}")
        return "seen / examples — " + "   ".join(parts) if parts else ""

    def _refresh_rows(self, cursor: int | None = None) -> None:
        self.query_one("#rows", PickList).set_rows(self._build_rows(), cursor)
        self.query_one("#suggest", Static).update(Text(self._suggestions(), style=DIM))

    # --- 儲存格 -------------------------------------------------------------- #
    def _cell_widgets(self) -> list:
        return [self.query_one(f"#cell-{i}") for i in range(len(self.spec.columns))]

    def _cells(self) -> list[str]:
        return [w.value for w in self._cell_widgets()]

    def _set_cells(self, cells: Sequence[str]) -> None:
        for w, value in zip(self._cell_widgets(), cells):
            if isinstance(w, CycleBox):
                if value in w.options:
                    w.value = value
                w.refresh()
            else:
                w.value = value
                w.cursor_position = len(value)

    def _clear_cells(self) -> None:
        for w in self._cell_widgets():
            if isinstance(w, CycleBox):
                w.reset()
            else:
                w.value = ""

    def on_mount(self) -> None:
        self._cell_widgets()[0].focus()

    # --- 動作 -------------------------------------------------------------- #
    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._commit_row()

    def on_cycle_box_submitted(self, event: CycleBox.Submitted) -> None:
        event.stop()
        self._commit_row()

    def _commit_row(self) -> None:
        inputs = [w for w in self._cell_widgets() if isinstance(w, Input)]
        if all(not w.value.strip() for w in inputs):
            if self._editing is not None:
                self._editing = None
                self._clear_cells()
                self.show_error()
                return
            self._finish()
            return
        cells = self._cells()
        error = M.check_table_row(self.field, self.spec, cells, self.items, self._editing)
        if error:
            self.show_error(error)
            return
        text = self.spec.format(cells)
        if self._editing is None:
            self.items.append(text)
            cursor = len(self.items) - 1
        else:
            self.items[self._editing] = text
            cursor = self._editing
            self._editing = None
        self._clear_cells()
        self.show_error()
        self._refresh_rows(cursor)
        self._cell_widgets()[0].focus()

    def _finish(self) -> None:
        errors = self.field.validate(self.items)
        if errors:
            self.show_error(errors[0])
            return
        self.accept(list(self.items))

    def action_focus_rows(self) -> None:
        if self.items and not isinstance(self.focused, PickList):
            self.query_one("#rows", PickList).focus()

    def on_pick_list_edge(self, event: PickList.Edge) -> None:
        event.stop()
        if event.direction < 0:
            self._cell_widgets()[0].focus()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        self._editing = event.index
        self._set_cells(self.spec.parse(self.items[event.index]))
        self._cell_widgets()[0].focus()

    def action_remove(self) -> None:
        if isinstance(self.focused, PickList):
            self._remove_current()

    def _remove_current(self) -> None:
        lst = self.query_one("#rows", PickList)
        if not self.items:
            return
        del self.items[lst.cursor]
        self._editing = None
        self._refresh_rows(lst.cursor)
        if not self.items:
            self._cell_widgets()[0].focus()

    def run_command(self, command: str) -> None:
        if command == "ok":
            self._finish()
        elif command == "remove":
            self._remove_current()
        else:
            super().run_command(command)


# ---------------------------------------------------------------------- #
class PresetDialog(Dialog):
    """艦隊 preset:單選(pvp)或複選(combat.fleet_presets,記錄順序)。"""

    def __init__(self, field: Field, value: Any, *, multi: bool,
                 tokens: Sequence[str] | None = None, hint: str = "") -> None:
        super().__init__()
        self.field = field
        self.value = value
        self.multi = multi
        self.tokens = list(tokens) if tokens else None
        self.hint = hint

    def compose(self) -> ComposeResult:
        f = self.field
        tokens = self.tokens or M.preset_tokens(multi=self.multi, nullable=f.nullable)
        with Vertical(classes="dlg"):
            yield from self.header(f.label, f.help)
            hint = self.hint or (
                "Space toggles a preset; the order you pick is the order saved. "
                "Enter = OK." if self.multi else
                "Arrows + Enter to choose. null = not used, 0 = unspecified.")
            yield _static(hint, classes="dlg-meta")
            yield PresetGrid(tokens, M.preset_selection(self.value),
                             multi=self.multi, id="grid")
            yield _static("", classes="dlg-meta", id="order")
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("OK", "ok"), ("Clear", "clear"), ("Cancel", "cancel"))

    def on_mount(self) -> None:
        self.query_one(PresetGrid).focus()
        self.set_interval(0.2, self._show_order)

    def _show_order(self) -> None:
        if not self.multi:
            return
        order = self.query_one(PresetGrid).order
        label = " → ".join(order) if order else "(none)"
        self.query_one("#order", Static).update(Text("order: " + label, style=DIM))

    def _result(self) -> Any:
        grid = self.query_one(PresetGrid)
        if self.multi:
            like = self.value if isinstance(self.value, list) else []
            return M.preset_value(grid.order, like)
        if not grid.order:
            return None if self.field.nullable else 0
        return M.preset_single_value(grid.order[0])

    def on_preset_grid_accepted(self, event: PresetGrid.Accepted) -> None:
        event.stop()
        self.accept(self._result())

    def run_command(self, command: str) -> None:
        if command == "ok":
            self.accept(self._result())
        elif command == "clear":
            grid = self.query_one(PresetGrid)
            grid.order = []
            grid.refresh()
        else:
            super().run_command(command)


# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class NumSpec:
    label: str
    value: int
    lo: Optional[int] = None
    hi: Optional[int] = None
    min_places: int = 1
    color: str = ""         # 該數字的顏色(標題與選中列)
    row: int = 0            # 排版:第幾排 / 第幾欄(配方 2×2 用)
    col: int = 0


class NumberDialog(Dialog):
    """逐位數滾動的數字選擇器(一個或多個數字)。

    ← → 換位數,↑ ↓ 滾動,Enter 確定。超出範圍會自動收斂到最大/最小值。
    單一數字回傳 int;多個數字(配方)回傳 list[int]。
    """

    HINT = "← →  digit    ↑ ↓  scroll    Tab  next number    Enter  OK    Esc  cancel"
    OVERHEAD = 16            # 滾輪以外的元件佔用的列數(含邊框)

    def __init__(self, field: Field, title: str, specs: Sequence[NumSpec], *,
                 as_list: bool) -> None:
        super().__init__()
        self.field = field
        self.title_text = title
        self.specs = list(specs)
        self.as_list = as_list
        # 依 spec 的順序存放:(起始滾輪, 有無正負號, 位數)。滾輪本身依畫面排版順序排列。
        self.groups: list[tuple[int, bool, int]] = [(0, False, 1)] * len(self.specs)

    def compose(self) -> ComposeResult:
        wheels: list[Wheel] = []
        order = sorted(range(len(self.specs)),
                       key=lambda i: (self.specs[i].row, self.specs[i].col))
        for gi in order:
            spec = self.specs[gi]
            signed, places = M.number_layout(spec.lo, spec.hi, spec.value, spec.min_places)
            start = len(wheels)
            value = M.clamp_number(spec.value, spec.lo, spec.hi)
            span = places + (1 if signed else 0)
            gap = spec.col > 0
            common = dict(span=span, row=spec.row, color=spec.color)
            if signed:
                wheels.append(Wheel(["+", "-"], 1 if value < 0 else 0, label=spec.label,
                                    gap_before=gap, **common))
            for pos, d in enumerate(M.digits_of(value, places)):
                first = pos == 0 and not signed
                wheels.append(Wheel([str(n) for n in range(10)], d,
                                    label=spec.label if first else "",
                                    gap_before=gap and first, **common))
            self.groups[gi] = (start, signed, places)
        f = self.field
        with Vertical(classes="dlg dlg-wide"):
            yield from self.header(self.title_text, f.help)
            yield _static(f"{f.key}   {M.type_label(f)}   default "
                          f"{M.format_value(f, f.default, 30)}", classes="dlg-meta")
            yield WheelPicker(wheels, id="wheels")
            yield _static("", classes="dlg-preview", id="preview")
            yield _static("", classes="dlg-err", id="err")
            yield _static(self.HINT, classes="dlg-meta")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def on_resize(self, event) -> None:
        Dialog.on_resize(self, event)
        picker = self.query_one(WheelPicker)
        picker.set_visible(5 if event.size.height - self.OVERHEAD >= picker.height_for(5) else 3)

    def on_mount(self) -> None:
        self.query_one(WheelPicker).focus()
        self._update_preview()

    # --- 讀寫滾輪 -------------------------------------------------------- #
    def _read(self, gi: int) -> int:
        picker = self.query_one(WheelPicker)
        start, signed, places = self.groups[gi]
        negative = False
        if signed:
            negative = picker.wheels[start].items[picker.wheels[start].index] == "-"
            start += 1
        digits = [int(picker.wheels[start + i].items[picker.wheels[start + i].index])
                  for i in range(places)]
        return M.number_from(negative, digits)

    def _write(self, gi: int, value: int) -> None:
        picker = self.query_one(WheelPicker)
        start, signed, places = self.groups[gi]
        if signed:
            picker.set_index(start, 1 if value < 0 else 0)
            start += 1
        for i, d in enumerate(M.digits_of(value, places)):
            picker.set_index(start + i, d)

    def _group_of(self, column: int) -> int:
        for gi, (start, signed, places) in enumerate(self.groups):
            if start <= column < start + places + (1 if signed else 0):
                return gi
        return 0

    def _values(self) -> list[int]:
        return [self._read(gi) for gi in range(len(self.groups))]

    def on_wheel_picker_changed(self, event: WheelPicker.Changed) -> None:
        event.stop()
        gi = self._group_of(event.column)
        spec = self.specs[gi]
        value = self._read(gi)
        clamped = M.clamp_number(value, spec.lo, spec.hi)
        if clamped != value:
            self._write(gi, clamped)
        self._update_preview()

    def _update_preview(self) -> None:
        values = self._values()
        spec = self.specs[0]
        if self.as_list:
            shown = "   ".join(f"{s.label} {v}" for s, v in zip(self.specs, values))
        else:
            rng = ""
            if spec.lo is not None or spec.hi is not None:
                rng = f"   (range {spec.lo if spec.lo is not None else '…'} .. " \
                      f"{spec.hi if spec.hi is not None else '…'})"
            shown = f"= {values[0]}{rng}"
        self.query_one("#preview", Static).update(Text(shown, style="bold #e5c07b"))

    def on_wheel_picker_accepted(self, event: WheelPicker.Accepted) -> None:
        event.stop()
        self._finish()

    def _finish(self) -> None:
        values = self._values()
        value: Any = values if self.as_list else values[0]
        errors = self.field.validate(value)
        if errors:
            self.show_error(errors[0])
            return
        self.accept(value)

    def run_command(self, command: str) -> None:
        if command == "ok":
            self._finish()
        else:
            super().run_command(command)


class MapDialog(Dialog):
    """出擊海域:世界 / 海域編號 / 目標節點三個滾輪(auto 時後兩者無效)。

    目標節點只提供 noro6 內「確實有對應預設」的選項,例如 2-2 有 B-2-2-A,
    就能選到 ``2-2-A``;「—」代表不指定節點(``2-2``)。
    """

    HINT = "← →  world / map / node    ↑ ↓  scroll    Enter  OK    Esc  cancel"

    def __init__(self, field: Field, value: Any,
                 nodes: Optional[M.NodeIndex] = None) -> None:
        super().__init__()
        self.field = field
        self.node_index = nodes or {}
        world, number, node = M.parse_map(value) or ("1", 1, "")
        self.world, self.number, self.node = world, number, node

    def compose(self) -> ComposeResult:
        f = self.field
        worlds = M.world_items(self.world)
        numbers = M.map_number_items(self.world, self.number)
        number_index = (self.number - 1) if self.number and self.world != "auto" else 0
        shown_number = numbers[min(number_index, len(numbers) - 1)]
        node_items = M.map_node_items(self.node_index, self.world, shown_number, self.node)
        node_index = node_items.index(self.node) if self.node in node_items else 0
        wheels = [
            Wheel(worlds, worlds.index(self.world), label="world", wrap=False),
            Wheel(numbers, min(number_index, len(numbers) - 1), label="map",
                  wrap=False, gap_before=True),
            Wheel(node_items, node_index, label="node", wrap=False, gap_before=True),
        ]
        with Vertical(classes="dlg"):
            yield from self.header(f.label, f.help)
            yield WheelPicker(wheels, id="wheels")
            yield _static("", classes="dlg-preview", id="preview")
            yield _static("", classes="dlg-meta", id="note")
            yield _static("", classes="dlg-err", id="err")
            yield _static(self.HINT, classes="dlg-meta")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def on_resize(self, event) -> None:
        Dialog.on_resize(self, event)
        picker = self.query_one(WheelPicker)
        picker.set_visible(5 if event.size.height - 17 >= picker.height_for(5) else 3)

    def on_mount(self) -> None:
        self.query_one(WheelPicker).focus()
        self._update_preview()

    def _current(self) -> str:
        world, number, node = self.query_one(WheelPicker).values()
        return M.build_map(world, number, node)

    def on_wheel_picker_changed(self, event: WheelPicker.Changed) -> None:
        event.stop()
        picker = self.query_one(WheelPicker)
        if event.column == 0:                       # 換世界 → 編號範圍跟著變
            world = picker.wheels[0].items[picker.wheels[0].index]
            old = picker.wheels[1]
            keep = old.index if old.items != ["—"] else 0
            picker.set_wheel(1, M.map_number_items(world), keep)
        if event.column in (0, 1):                  # 換世界或編號 → 節點選項重算
            world, number, _ = picker.values()
            picker.set_wheel(2, M.map_node_items(self.node_index, world, number), 0)
        self._update_preview()

    def _update_preview(self) -> None:
        picker = self.query_one(WheelPicker)
        world, number, node = picker.values()
        self.query_one("#preview", Static).update(
            Text("= " + self._current(), style="bold #e5c07b"))
        options = [n for n in picker.wheels[2].items if n != M.NO_NODE]
        if world == "auto":
            note = ""
        elif options:
            note = "noro6 node presets for this map: " + ", ".join(options)
        else:
            note = "No node-specific noro6 preset for this map."
        self.query_one("#note", Static).update(Text(note, style=DIM))

    def on_wheel_picker_accepted(self, event: WheelPicker.Accepted) -> None:
        event.stop()
        self._finish()

    def _finish(self) -> None:
        value = self._current()
        errors = self.field.validate(value)
        if errors:
            self.show_error(errors[0])
            return
        self.accept(value)

    def run_command(self, command: str) -> None:
        if command == "ok":
            self._finish()
        else:
            super().run_command(command)


# ---------------------------------------------------------------------- #
class QuestDialog(Dialog):
    """任務勾選清單,依前綴分組。Space 勾選(在群組標題上 = 整組),Enter 確定。"""

    FIT = {"quests": (14, 14)}

    def __init__(self, field: Field, selected: Sequence[Any],
                 catalog: Sequence[M.QuestInfo]) -> None:
        super().__init__()
        self.field = field
        self.old = list(selected)
        self.chosen: set[str] = {str(s) for s in selected}
        self.groups = M.group_quests(catalog, selected)
        self.notes = {q.id: q.note for q in catalog}
        self._row_ids: list[tuple[str, Optional[str]]] = []     # (群組, 任務 ID 或 None=標題)

    BINDINGS = [
        *Dialog.BINDINGS,
        Binding("a", "group(1)", show=False),
        Binding("n", "group(0)", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg"):
            yield from self.header(self.field.label, self.field.help)
            yield _static("Space = tick · a / n = all / none in group · Enter = OK",
                          classes="dlg-meta")
            yield PickList(self._build_rows(), max_visible=14, id="quests")
            yield _static("", classes="dlg-meta", id="count")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def _build_rows(self) -> list[Row]:
        rows, self._row_ids = [], []
        for group, ids in self.groups:
            n = sum(1 for i in ids if i in self.chosen)
            rows.append(Row(f"── {M.quest_group_title(group)}  ({n}/{len(ids)}) ──",
                            toggle=True, style="bold #e5c07b"))
            self._row_ids.append((group, None))
            for qid in ids:
                note = self.notes.get(qid, "")
                rows.append(Row(f"{qid:<8} {note}".rstrip(), checked=qid in self.chosen,
                                toggle=True))
                self._row_ids.append((group, qid))
        return rows

    def _redraw(self) -> None:
        lst = self.query_one("#quests", PickList)
        lst.set_rows(self._build_rows(), lst.cursor)
        self.query_one("#count", Static).update(Text(f"{len(self.chosen)} selected", style=DIM))

    def on_mount(self) -> None:
        self.query_one("#quests", PickList).focus()
        self._redraw()

    def _group_ids(self, group: str) -> list[str]:
        return next((ids for g, ids in self.groups if g == group), [])

    def _set_group(self, group: str, on: bool) -> None:
        for qid in self._group_ids(group):
            (self.chosen.add if on else self.chosen.discard)(qid)

    def on_pick_list_toggled(self, event: PickList.Toggled) -> None:
        event.stop()
        group, qid = self._row_ids[event.index]
        if qid is None:
            ids = self._group_ids(group)
            self._set_group(group, not all(i in self.chosen for i in ids))
        elif qid in self.chosen:
            self.chosen.discard(qid)
        else:
            self.chosen.add(qid)
        self._redraw()

    def action_group(self, on: int) -> None:
        lst = self.query_one("#quests", PickList)
        if 0 <= lst.cursor < len(self._row_ids):
            self._set_group(self._row_ids[lst.cursor][0], bool(on))
            self._redraw()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        self._finish()

    def _finish(self) -> None:
        order = [q for _, ids in self.groups for q in ids if q in self.chosen]
        self.accept(M.merge_selection(self.old, order))

    def run_command(self, command: str) -> None:
        if command == "ok":
            self._finish()
        else:
            super().run_command(command)


# ---------------------------------------------------------------------- #
class JsonDialog(Dialog):
    """JSON 編輯器(ship_switcher.slots、未知 key)。Ctrl+S 或點 OK 套用。"""

    BINDINGS = [*Dialog.BINDINGS, Binding("ctrl+s", "apply", show=False)]

    def __init__(self, title: str, help_text: str, value: Any, *, want_object: bool) -> None:
        super().__init__()
        self.title_text, self.help_text = title, help_text
        self.value = value
        self.want_object = want_object

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg dlg-wide"):
            yield from self.header(self.title_text, self.help_text)
            if TextArea is not None:
                yield TextArea(M.dump_json(self.value), id="json")
            else:                                           # pragma: no cover
                import json
                yield Input(value=json.dumps(self.value, ensure_ascii=False), id="json")
            yield _static("", classes="dlg-err", id="err")
            yield _static("Ctrl+S = apply · Esc = cancel", classes="dlg-meta")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def on_mount(self) -> None:
        self.query_one("#json").focus()
        self._check()

    def _text(self) -> str:
        widget = self.query_one("#json")
        return widget.text if TextArea is not None and isinstance(widget, TextArea) else widget.value

    def _check(self) -> Any:
        try:
            value = M.parse_json(self._text(), want_object=self.want_object)
        except M.ParseError as exc:
            self.show_error(str(exc))
            return M.ParseError
        self.show_error()
        return value

    def on_text_area_changed(self, event) -> None:
        event.stop()
        self._check()

    def on_input_changed(self, event: Input.Changed) -> None:       # pragma: no cover
        event.stop()
        self._check()

    def action_apply(self) -> None:
        value = self._check()
        if value is not M.ParseError:
            self.accept(value)

    def run_command(self, command: str) -> None:
        if command == "ok":
            self.action_apply()
        else:
            super().run_command(command)


# ---------------------------------------------------------------------- #
class ValueDialog(Dialog):
    """單行文字輸入(字串、小數、key 名稱)。parse(text) → (值, 錯誤訊息)。"""

    def __init__(self, title: str, help_text: str, initial: str,
                 parse: Callable[[str], tuple[Any, str]]) -> None:
        super().__init__()
        self.title_text, self.help_text = title, help_text
        self.initial = initial
        self.parse = parse

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg"):
            yield from self.header(self.title_text, self.help_text)
            yield Input(value=self.initial, id="value")
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def on_mount(self) -> None:
        box = self.query_one(Input)
        box.focus()
        box.cursor_position = len(self.initial)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        _, error = self.parse(event.value)
        self.show_error(error)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._submit()

    def _submit(self) -> None:
        value, error = self.parse(self.query_one(Input).value)
        if error:
            self.show_error(error)
            return
        self.accept(value)

    def run_command(self, command: str) -> None:
        if command == "ok":
            self._submit()
        else:
            super().run_command(command)


_KIND_HELP = {
    "str": "text", "int": "whole number (wheel)", "float": "decimal number",
    "bool": "on / off", "null": "empty value", "object": "group of named items { }",
    "list": "ordered list [ ]",
}


class NewItemDialog(Dialog):
    """新增樹狀項目:object 底下要先輸入 key,再選型別;list 底下只選型別。"""

    FIT = {"kinds": (13, 7)}

    def __init__(self, needs_key: bool, existing: Sequence[Any]) -> None:
        super().__init__()
        self.needs_key = needs_key
        self.existing = list(existing)

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg"):
            yield _static("Add item" if self.needs_key else "Add list item", classes="dlg-title")
            if self.needs_key:
                yield Input(placeholder="key name, then Enter", id="key")
            rows = [Row(f"{k:<7} {_KIND_HELP[k]}") for k in TR.KINDS]
            yield PickList(rows, max_visible=7, id="kinds")
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("Cancel", "cancel"))

    def on_mount(self) -> None:
        if self.needs_key:
            self.query_one("#key", Input).focus()
        else:
            self.query_one("#kinds", PickList).focus()

    def _key_problem(self) -> str:
        if not self.needs_key:
            return ""
        key = self.query_one("#key", Input).value.strip()
        return TR.key_error({k: 1 for k in self.existing}, key) or ""

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        problem = self._key_problem()
        if problem:
            self.show_error(problem)
            return
        self.show_error()
        self.query_one("#kinds", PickList).focus()

    def action_focus_kinds(self) -> None:
        if isinstance(self.focused, Input):
            self.query_one("#kinds", PickList).focus()

    BINDINGS = [*Dialog.BINDINGS, Binding("down", "focus_kinds", show=False)]

    def on_pick_list_edge(self, event: PickList.Edge) -> None:
        event.stop()
        if event.direction < 0 and self.needs_key:
            self.query_one("#key", Input).focus()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        problem = self._key_problem()
        if problem:
            self.show_error(problem)
            self.query_one("#key", Input).focus()
            return
        key = self.query_one("#key", Input).value.strip() if self.needs_key else None
        self.accept((key, TR.KINDS[event.index]))


class TreeDialog(Dialog):
    """JSON 的樹狀表格編輯:展開 / 收合、新增、改名、刪除、改型別,數字用滾輪。

    給結構不固定的設定用(ship_switcher.slots、未知 key)。結構已知的欄位請用專用控制項。
    """

    FIT = {"tree": (15, 12)}
    HINT = ("↑↓ move  →← open/close  Enter edit  a add  x remove  r rename  t type  "
            "j raw JSON  Ctrl+S apply  Esc cancel")

    BINDINGS = [
        *Dialog.BINDINGS,
        Binding("a", "add", show=False),
        Binding("x,delete", "remove", show=False),
        Binding("r", "rename", show=False),
        Binding("t", "retype", show=False),
        Binding("j", "raw_json", show=False),
        Binding("right", "open_node", show=False),
        Binding("left", "close_node", show=False),
        Binding("ctrl+s", "apply", show=False),
    ]

    def __init__(self, title: str, help_text: str, value: Any, *,
                 field: Optional[Field] = None) -> None:
        super().__init__()
        self.title_text, self.help_text = title, help_text
        self.field = field
        self.doc: Any = TR.make_working_copy(value)
        self.root_kind = TR.kind_of(value)
        self.expanded = TR.initial_expanded(self.doc)
        self.flat: list[TR.TreeRow] = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg dlg-wide"):
            yield from self.header(self.title_text, self.help_text)
            yield _static("", classes="dlg-meta", id="crumb")
            yield PickList([], max_visible=12, empty="(empty)  —  press a to add", id="tree")
            yield _static("", classes="dlg-err", id="err")
            yield _static(self.HINT, classes="dlg-meta")
            yield self.buttons(("OK", "ok"), ("Add", "add"), ("Remove", "remove"),
                               ("Cancel", "cancel"))

    def on_mount(self) -> None:
        self._rebuild()
        self.query_one("#tree", PickList).focus()

    # --- 表格 ------------------------------------------------------------- #
    def _tree(self) -> PickList:
        return self.query_one("#tree", PickList)

    def _selected(self) -> Optional[TR.TreeRow]:
        lst = self._tree()
        return self.flat[lst.cursor] if self.flat and 0 <= lst.cursor < len(self.flat) else None

    def _rebuild(self, select: Optional[TR.Path] = None) -> None:
        lst = self._tree()
        keep = lst.cursor
        self.flat = TR.flatten(self.doc, self.expanded)
        width = max(lst.size.width, 30)
        key_w = TR.key_column_width(self.flat, width)
        rows = [Row(TR.row_text(r, key_w, width),
                    toggle=r.expandable or r.kind == "bool") for r in self.flat]
        cursor = keep
        if select is not None:
            for i, r in enumerate(self.flat):
                if r.path == select:
                    cursor = i
                    break
        lst.set_rows(rows, min(cursor, max(0, len(rows) - 1)))
        self._update_crumb()

    def _update_crumb(self) -> None:
        row = self._selected()
        text = TR.path_text(row.path) if row else TR.path_text(())
        self.query_one("#crumb", Static).update(Text(text, style=DIM))

    def on_pick_list_moved(self, event) -> None:       # 預留:游標移動時更新路徑
        self._update_crumb()

    # --- 展開 / 收合 ------------------------------------------------------ #
    def _toggle_open(self, row: TR.TreeRow) -> None:
        if row.path in self.expanded:
            self.expanded.discard(row.path)
        else:
            self.expanded.add(row.path)
        self._rebuild(row.path)

    def action_open_node(self) -> None:
        row = self._selected()
        if row and row.expandable and not row.expanded:
            self._toggle_open(row)

    def action_close_node(self) -> None:
        row = self._selected()
        if row is None:
            return
        if row.expanded:
            self._toggle_open(row)
        elif len(row.path) > 1:                         # 回到上一層
            self._rebuild(TR.parent_path(row.path))

    def on_pick_list_toggled(self, event: PickList.Toggled) -> None:
        event.stop()
        row = self.flat[event.index]
        if row.expandable:
            self._toggle_open(row)
        elif row.kind == "bool":
            TR.set_at(self.doc, row.path, not row.value)
            self._rebuild(row.path)

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        self._activate(self.flat[event.index])

    def _activate(self, row: TR.TreeRow) -> None:
        """Enter:容器 = 展開/收合;布林 = 切換;其他 = 開編輯器。"""
        if row.expandable:
            self._toggle_open(row)
        elif row.kind == "bool":
            TR.set_at(self.doc, row.path, not row.value)
            self._rebuild(row.path)
        else:
            self._edit(row)

    # --- 編輯值 ----------------------------------------------------------- #
    def _edit(self, row: TR.TreeRow) -> None:
        label = TR.path_text(row.path)
        done = partial(self._edited, row.path)
        if row.kind == "int":
            limit = max(9_999_999, 10 ** len(str(abs(row.value))) - 1)
            field = Field(label, Kind.INT, 0, label, "", min=-limit, max=limit)
            self.app.push_screen(
                NumberDialog(field, label, [NumSpec("value", row.value, -limit, limit)],
                             as_list=False), done)
        elif row.kind == "float":
            self.app.push_screen(ValueDialog(label, "Decimal number", repr(row.value),
                                             _parse_float), done)
        elif row.kind == "str":
            self.app.push_screen(ValueDialog(label, "Text", row.value,
                                             lambda text: (text, "")), done)
        else:                                           # null → 選一個型別
            self.action_retype()

    def _edited(self, path: TR.Path, result: Optional[Picked]) -> None:
        if result is not None:
            TR.set_at(self.doc, path, result.value)
            self._rebuild(path)

    # --- 新增 / 刪除 / 改名 / 改型別 -------------------------------------- #
    def _container_target(self) -> TR.Path:
        row = self._selected()
        if row is None:
            return ()
        return row.path if row.expandable else TR.parent_path(row.path)

    def action_add(self) -> None:
        target = self._container_target()
        container = TR.get_at(self.doc, target)
        self.app.push_screen(
            NewItemDialog(isinstance(container, dict),
                          list(container) if isinstance(container, dict) else []),
            partial(self._added, target))

    def _added(self, target: TR.Path, result: Optional[Picked]) -> None:
        if result is None:
            return
        key, kind = result.value
        path = TR.add_child(self.doc, target, key, TR.default_for(kind))
        if target:
            self.expanded.add(target)
        if kind in TR.CONTAINERS:
            self.expanded.add(path)
        self._rebuild(path)
        row = self._selected()
        if row is not None and row.kind in ("str", "int", "float"):
            self._edit(row)                             # 新增完直接輸入內容

    def action_remove(self) -> None:
        row = self._selected()
        if row is None:
            return
        TR.delete_at(self.doc, row.path)
        self.expanded = {p for p in self.expanded if p[:len(row.path)] != row.path}
        self._rebuild()

    def action_rename(self) -> None:
        row = self._selected()
        if row is None or not isinstance(row.key, str):
            return
        parent = TR.get_at(self.doc, TR.parent_path(row.path))

        def parse(text: str) -> tuple[Any, str]:
            return text.strip(), TR.key_error(parent, text.strip(), row.key) or ""

        self.app.push_screen(ValueDialog("Rename key", TR.path_text(row.path), row.key, parse),
                             partial(self._renamed, row))

    def _renamed(self, row: TR.TreeRow, result: Optional[Picked]) -> None:
        if result is None or result.value == row.key:
            return
        new_path = TR.rename_key(self.doc, row.path, result.value)
        self.expanded = {new_path + p[len(row.path):] if p[:len(row.path)] == row.path else p
                         for p in self.expanded}
        self._rebuild(new_path)

    def action_retype(self) -> None:
        row = self._selected()
        if row is None:
            return
        options = [(f"{k:<7} {_KIND_HELP[k]}", k) for k in TR.KINDS]
        self.app.push_screen(
            ChoiceDialog("Change type", "Content is kept when it converts cleanly "
                         "(\"12\" → 12); otherwise the new type starts empty.",
                         options, row.kind),
            partial(self._retyped, row))

    def _retyped(self, row: TR.TreeRow, result: Optional[Picked]) -> None:
        if result is None or result.value == row.kind:
            return
        TR.set_at(self.doc, row.path, TR.convert(row.value, result.value))
        self._rebuild(row.path)

    # --- 原始 JSON / 套用 --------------------------------------------------- #
    def action_raw_json(self) -> None:
        self.app.push_screen(
            JsonDialog(self.title_text, "Raw JSON", self.doc,
                       want_object=isinstance(self.doc, dict)), self._raw_done)

    def _raw_done(self, result: Optional[Picked]) -> None:
        if result is None:
            return
        self.doc = result.value
        self.expanded = TR.initial_expanded(self.doc)
        self._rebuild()

    def action_apply(self) -> None:
        self._finish()

    def _finish(self) -> None:
        if TR.kind_of(self.doc) != self.root_kind:
            self.show_error(f"Top level must stay a {self.root_kind}")
            return
        if self.field is not None:
            errors = self.field.validate(self.doc)
            if errors:
                self.show_error(errors[0])
                return
        self.accept(self.doc)

    def run_command(self, command: str) -> None:
        if command == "ok":
            self._finish()
        elif command == "add":
            self.action_add()
        elif command == "remove":
            self.action_remove()
        else:
            super().run_command(command)


def _parse_float(text: str) -> tuple[Any, str]:
    try:
        return float(text), ""
    except ValueError:
        return None, "Enter a number such as 1.5"


# ---------------------------------------------------------------------- #
class DangerDialog(Dialog):
    """高風險設定的二次確認。y / n。"""

    BINDINGS = [
        Binding("y", "answer(1)", show=False),
        Binding("n,escape", "answer(0)", show=False),
    ]

    def __init__(self, field: Field, added: Sequence[Any]) -> None:
        super().__init__()
        self.field = field
        self.added = list(added)

    def compose(self) -> ComposeResult:
        body = Text()
        body.append("⚠ Dangerous setting\n", style="bold #e06c75")
        body.append(f"{self.field.label}\n", style="bold")
        body.append(self.field.help + "\n\n")
        if self.added:
            body.append("Adding: " + ", ".join(str(a) for a in self.added) + "\n\n",
                        style="#e5c07b")
        body.append("Apply this change?")
        with Vertical(classes="dlg dlg-danger"):
            yield Static(body)
            yield Horizontal(ActionLabel("Apply", "yes", hotkey="y"),
                             ActionLabel("Cancel", "no", hotkey="n"), classes="dlg-buttons")

    def action_answer(self, yes: int) -> None:
        self.dismiss(bool(yes))

    def run_command(self, command: str) -> None:
        self.dismiss(command == "yes")


# ---------------------------------------------------------------------- #
class SearchDialog(Dialog):
    """/ 搜尋全部欄位。↑↓ 選擇,Enter 跳過去。"""

    FIT = {"hits": (10, 12)}

    BINDINGS = [
        *Dialog.BINDINGS,
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
    ]

    def __init__(self, unknown_keys: Sequence[str] = ()) -> None:
        super().__init__()
        self.unknown = list(unknown_keys)
        self.hits: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg dlg-wide"):
            yield _static("Search settings", classes="dlg-title")
            yield Input(placeholder="key, label or description…", id="q")
            yield PickList([], max_visible=12, empty="type to search", id="hits")
            yield _static("↑↓ select · Enter jump · Esc close", classes="dlg-meta")

    def on_mount(self) -> None:
        self.query_one("#q", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        query = event.value.strip().lower()
        fields = M.search_fields(query)
        self.hits = [f.key for f in fields]
        rows = [Row(M.pad_cells(f.key, 34) + " " + f.label) for f in fields]
        if query:
            for key in self.unknown:
                if query in key.lower():
                    self.hits.append(key)
                    rows.append(Row(M.pad_cells(key, 34) + " (unknown key)"))
        lst = self.query_one("#hits", PickList)
        lst.empty = "no match" if query else "type to search"
        lst.set_rows(rows, 0)

    def action_move(self, delta: int) -> None:
        self.query_one("#hits", PickList).move_cursor(delta)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._jump()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        self._jump()

    def _jump(self) -> None:
        lst = self.query_one("#hits", PickList)
        if self.hits and 0 <= lst.cursor < len(self.hits):
            self.accept(self.hits[lst.cursor])
