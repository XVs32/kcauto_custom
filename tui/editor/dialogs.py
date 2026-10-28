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
from typing import Any, Optional, Sequence

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
from .widgets import ActionLabel, CycleBox, PickList, PresetGrid, Row

ERR = "bold #e06c75"
DIM = "#6b7280"


@dataclass(frozen=True)
class Picked:
    value: Any


def _static(text: str | Text, *, classes: str = "", id: str | None = None) -> Static:
    return Static(text if isinstance(text, Text) else Text(text), classes=classes, id=id)


class Dialog(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

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
            yield PickList(self._rows(), max_visible=8, id="items")
            yield Input(placeholder="type an item, Enter to add — empty Enter = OK", id="add")
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("OK", "ok"), ("Remove", "remove"), ("Cancel", "cancel"))

    def _rows(self) -> list[Row]:
        return [Row(f"{i + 1:>2}. {item}") for i, item in enumerate(self.items)]

    def _refresh_rows(self, cursor: int | None = None) -> None:
        self.query_one("#items", PickList).set_rows(self._rows(), cursor)

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
            yield PickList(self._rows(), max_visible=8, id="rows")
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

    def _rows(self) -> list[Row]:
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
        self.query_one("#rows", PickList).set_rows(self._rows(), cursor)
        self.query_one("#suggest", Static).update(Text(self._suggestions(), style=DIM))

    # --- 儲存格 -------------------------------------------------------------- #
    def _widgets(self) -> list:
        return [self.query_one(f"#cell-{i}") for i in range(len(self.spec.columns))]

    def _cells(self) -> list[str]:
        return [w.value for w in self._widgets()]

    def _set_cells(self, cells: Sequence[str]) -> None:
        for w, value in zip(self._widgets(), cells):
            if isinstance(w, CycleBox):
                if value in w.options:
                    w.value = value
                w.refresh()
            else:
                w.value = value
                w.cursor_position = len(value)

    def _clear_cells(self) -> None:
        for w in self._widgets():
            if isinstance(w, CycleBox):
                w.reset()
            else:
                w.value = ""

    def on_mount(self) -> None:
        self._widgets()[0].focus()

    # --- 動作 -------------------------------------------------------------- #
    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._commit_row()

    def on_cycle_box_submitted(self, event: CycleBox.Submitted) -> None:
        event.stop()
        self._commit_row()

    def _commit_row(self) -> None:
        inputs = [w for w in self._widgets() if isinstance(w, Input)]
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
        self._widgets()[0].focus()

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
            self._widgets()[0].focus()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        self._editing = event.index
        self._set_cells(self.spec.parse(self.items[event.index]))
        self._widgets()[0].focus()

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
            self._widgets()[0].focus()

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

    def __init__(self, field: Field, value: Any, *, multi: bool) -> None:
        super().__init__()
        self.field = field
        self.value = value
        self.multi = multi

    def compose(self) -> ComposeResult:
        f = self.field
        tokens = M.preset_tokens(multi=self.multi, nullable=f.nullable)
        with Vertical(classes="dlg"):
            yield from self.header(f.label, f.help)
            hint = ("Space toggles a preset; the order you pick is the order saved. "
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
class RecipeDialog(Dialog):
    """資源配方:燃料 / 彈藥 / 鋼材 / 鋁土 四個整數。Tab 換欄,Enter 確定。"""

    NAMES = (("fuel", "#8fbf6a"), ("ammo", "#c9a26b"), ("steel", "#9aa5b1"), ("bauxite", "#d19a66"))

    def __init__(self, field: Field, value: Any) -> None:
        super().__init__()
        self.field = field
        self.value = value if isinstance(value, list) and len(value) == 4 else field.make_default()

    def compose(self) -> ComposeResult:
        f = self.field
        with Vertical(classes="dlg"):
            yield from self.header(f.label, f.help)
            with Horizontal(id="recipe"):
                for i, (name, color) in enumerate(self.NAMES):
                    with Vertical(classes="recipe-col"):
                        yield _static(Text(name, style=color))
                        yield Input(value=str(self.value[i]), id=f"r{i}")
            yield _static("Tab = next field · Enter = OK", classes="dlg-meta")
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def on_mount(self) -> None:
        self.query_one("#r0", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._submit()

    def _submit(self) -> None:
        values = []
        for i, (name, _) in enumerate(self.NAMES):
            text = self.query_one(f"#r{i}", Input).value.strip()
            if not re.fullmatch(r"-?\d+", text):
                self.show_error(f"{name}: enter a whole number")
                return
            values.append(int(text))
        errors = self.field.validate(values)
        if errors:
            self.show_error(errors[0])
            return
        self.accept(values)

    def run_command(self, command: str) -> None:
        if command == "ok":
            self._submit()
        else:
            super().run_command(command)


# ---------------------------------------------------------------------- #
class QuestDialog(Dialog):
    """任務勾選清單,依前綴分組。Space 勾選(在群組標題上 = 整組),Enter 確定。"""

    def __init__(self, field: Field, selected: Sequence[Any], catalog: Sequence[str]) -> None:
        super().__init__()
        self.field = field
        self.old = list(selected)
        self.chosen: set[str] = {str(s) for s in selected}
        self.groups = M.group_quests(catalog, selected)
        self._ids: list[tuple[str, Optional[str]]] = []     # (群組, 任務 ID 或 None=標題)

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
            yield PickList(self._rows(), max_visible=14, id="quests")
            yield _static("", classes="dlg-meta", id="count")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def _rows(self) -> list[Row]:
        rows, self._ids = [], []
        for group, ids in self.groups:
            n = sum(1 for i in ids if i in self.chosen)
            rows.append(Row(f"── {group}  ({n}/{len(ids)}) ──", toggle=True, style="bold #e5c07b"))
            self._ids.append((group, None))
            for qid in ids:
                rows.append(Row(qid, checked=qid in self.chosen, toggle=True))
                self._ids.append((group, qid))
        return rows

    def _redraw(self) -> None:
        lst = self.query_one("#quests", PickList)
        lst.set_rows(self._rows(), lst.cursor)
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
        group, qid = self._ids[event.index]
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
        if 0 <= lst.cursor < len(self._ids):
            self._set_group(self._ids[lst.cursor][0], bool(on))
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
