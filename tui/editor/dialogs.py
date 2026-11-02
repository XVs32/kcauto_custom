"""Editor dialogs (ModalScreen).

Shared conventions
  * Cancel (Esc / click Cancel) → dismiss(None); confirm → dismiss(Picked(value)).
    The result is wrapped in ``Picked`` because ``None`` itself (null) is also a valid field value.
  * Enter inside an input box: with content = add / confirm that entry; empty = press OK.
  * Arrow keys: ↓ in the input box enters the list, ↑ at the top of the list returns to the input box.
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
from textual.widget import Widget
from textual.widgets import Input, Static

try:  # TextArea needs a newer Textual; without it fall back to a single-line input
    from textual.widgets import TextArea
except ImportError:  # pragma: no cover
    TextArea = None

from ..i18n import t
from ..schema import Field, Kind
from ..schema.scheduler_rule import parse_rule
from . import model as M
from . import narrow as N
from . import tree as TR
from .widgets import (
    ActionLabel,
    CycleBox,
    PickList,
    PresetGrid,
    Row,
    Wheel,
    WheelPicker,
)

ERR = "bold #e06c75"
DIM = "#6b7280"


@dataclass(frozen=True)
class Picked:
    value: Any


def _static(text: str | Text, *, classes: str = "", id: str | None = None) -> Static:
    return Static(
        text if isinstance(text, Text) else Text(text), classes=classes, id=id
    )


class Dialog(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    # list widget id → (rows taken by widgets other than the list, default maximum rows shown).
    # On a short terminal the list is shortened to the window height, so the bottom OK / Cancel is not cut off.
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

    # --- list ↔ bottom buttons: ↓ past the end of the list moves to the buttons, ↑ on the buttons returns to the list --- #
    _before_buttons: Optional[Widget] = None

    def focus_buttons(self, source: Optional[Widget] = None) -> bool:
        labels = list(self.query(ActionLabel))
        if not labels:
            return False
        self._before_buttons = source
        labels[0].focus()
        return True

    def return_from_buttons(self) -> None:
        target = self._before_buttons
        if target is None or not getattr(target, "is_attached", True):
            lists = list(self.query(PickList))
            target = lists[0] if lists else None
        if target is not None:
            target.focus()

    def on_pick_list_edge(self, event: PickList.Edge) -> None:
        if event.direction > 0:
            event.stop()
            self.focus_buttons(event.source)

    def accept(self, value: Any) -> None:
        self.dismiss(Picked(value))

    def run_command(self, command: str) -> None:  # overridden by subclasses
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
        return Horizontal(
            *(ActionLabel(label, cmd) for label, cmd in items), classes="dlg-buttons"
        )


# ---------------------------------------------------------------------- #
class ChoiceDialog(Dialog):
    """Single-choice list (enum)."""

    FIT = {"choices": (11, 12)}

    def __init__(
        self,
        title: str,
        help_text: str,
        options: Sequence[tuple[str, Any]],
        current: Any,
    ) -> None:
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
    """Single-line input for int / int|str / str. Integers can be nudged with ↑↓."""

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
            yield _static(
                t(
                    "{key}   {type}   default {default}",
                    key=f.key,
                    type=M.type_label(f),
                    default=M.format_value(f, f.default, 30),
                ),
                classes="dlg-meta",
            )
            yield Input(
                value="" if self.current is None else str(self.current), id="value"
            )
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
    """Array of strings / integers (chip list). The input box accepts several items pasted at once (separated by commas or spaces)."""

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
                yield _static(t("format: {hint}", hint=f._hint()), classes="dlg-meta")
            if f.lengths:
                yield _static(
                    t(
                        "count must be {allowed}",
                        allowed=t(" or ").join(str(n) for n in f.lengths),
                    ),
                    classes="dlg-meta",
                )
            yield PickList(self._build_rows(), max_visible=8, id="items")
            yield Input(
                placeholder=t("type an item, Enter to add — empty Enter = OK"), id="add"
            )
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("OK", "ok"), ("Remove", "remove"), ("Cancel", "cancel"))

    def _build_rows(self) -> list[Row]:
        return [Row(f"{i + 1:>2}. {item}") for i, item in enumerate(self.items)]

    def _refresh_rows(self, cursor: int | None = None) -> None:
        self.query_one("#items", PickList).set_rows(self._build_rows(), cursor)

    def on_mount(self) -> None:
        self.query_one("#add", Input).focus()

    # --- input ------------------------------------------------------------- #
    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        text = event.value.strip()
        if not text:
            if (
                self._editing is not None
            ):  # clearing it halfway through editing = abandon this edit
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
        added = staged[len(base) :]
        if self._editing is None:
            self.items.extend(added)
            cursor = len(self.items) - 1
        else:
            at = self._editing
            self.items[at : at + 1] = added
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

    # --- list -------------------------------------------------------------- #
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
        """Enter: put the item back into the input box for editing."""
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
    """Multi-column table: each row is one string joined by a separator (A>B, A:line_ahead, schedule rules, ...)."""

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

    # --- screen ------------------------------------------------------------- #
    def compose(self) -> ComposeResult:
        f, spec = self.field, self.spec
        with Vertical(classes="dlg dlg-wide"):
            yield from self.header(f.label, f.help)
            if spec.note:
                yield _static(t(spec.note), classes="dlg-meta")
            yield _static(self._header_line(), classes="dlg-colhead")
            yield PickList(self._build_rows(), max_visible=8, id="rows")
            with Horizontal(id="cells"):
                for i, col in enumerate(spec.columns):
                    if col.choices:
                        yield CycleBox(col.choices, id=f"cell-{i}")
                    else:
                        yield Input(
                            placeholder=col.name + ("?" if col.optional else ""),
                            id=f"cell-{i}",
                        )
            yield _static(self._suggestions(), classes="dlg-meta", id="suggest")
            yield _static("", classes="dlg-err", id="err")
            yield self.buttons(("OK", "ok"), ("Remove", "remove"), ("Cancel", "cancel"))

    def _header_line(self) -> str:
        return "    " + " │ ".join(
            M.pad_cells(c.name, c.width) for c in self.spec.columns
        )

    def _build_rows(self) -> list[Row]:
        rows = []
        for i, item in enumerate(self.items):
            cells = self.spec.parse(item)
            body = " │ ".join(
                M.pad_cells(c, col.width) for c, col in zip(cells, self.spec.columns)
            )
            rows.append(Row(f"{i + 1:>2}. {body}"))
        return rows

    def _suggestions(self) -> str:
        return ""

    def _refresh_rows(self, cursor: int | None = None) -> None:
        self.query_one("#rows", PickList).set_rows(self._build_rows(), cursor)
        self.query_one("#suggest", Static).update(Text(self._suggestions(), style=DIM))

    # --- cells -------------------------------------------------------------- #
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

    # --- actions ------------------------------------------------------------ #
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
        error = M.check_table_row(
            self.field, self.spec, cells, self.items, self._editing
        )
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
    """Fleet preset: single choice (pvp) or multiple choice (combat.fleet_presets, order is recorded)."""

    def __init__(
        self,
        field: Field,
        value: Any,
        *,
        multi: bool,
        tokens: Sequence[str] | None = None,
        hint: str = "",
    ) -> None:
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
                t(
                    "Space toggles a preset; the order you pick is the order saved. Enter = OK."
                )
                if self.multi
                else t("Arrows + Enter to choose. null = not used, 0 = unspecified.")
            )
            yield _static(hint, classes="dlg-meta")
            yield PresetGrid(
                tokens, M.preset_selection(self.value), multi=self.multi, id="grid"
            )
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
        label = " → ".join(order) if order else t("(none)")
        self.query_one("#order", Static).update(Text(t("order: ") + label, style=DIM))

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
    color: str = ""  # colour of this number (title and selected row)
    row: int = 0  # layout: which row / column (used by the 2×2 recipe)
    col: int = 0


class NumberDialog(Dialog):
    """Digit-by-digit scrolling number picker (one or more numbers).

    ← → change digit, ↑ ↓ scroll, Enter confirms. Out-of-range values are clamped to the maximum / minimum.
    A single number returns an int; several numbers (recipe) return a list[int].
    """

    HINT = "← →  digit    ↑ ↓  scroll    Enter  OK    Esc  cancel"
    # several numbers (recipe) have two levels: pick a resource first, Enter goes in to adjust the number
    HINT_GROUP = "↑ ↓ ← →  choose    Enter  edit this one    Tab  next    Esc  cancel"
    HINT_DIGIT = "← →  digit    ↑ ↓  scroll    Enter  confirm    Esc  undo this one"
    OVERHEAD = 16  # rows used by widgets other than the wheels (including border)
    PRESET_ROWS = 7  # extra rows taken when the preset list is stacked above the wheels
    SIDE_BY_SIDE = 92  # the terminal must be at least this wide for the presets to go left of the wheels
    BINDINGS = [
        *Dialog.BINDINGS,
        Binding("p", "focus_presets", show=False),
        Binding("right", "from_presets", show=False),
    ]
    stacked = (
        False  # the preset list is currently stacked above the wheels (narrow terminal)
    )

    def __init__(
        self,
        field: Field,
        title: str,
        specs: Sequence[NumSpec],
        *,
        as_list: bool,
        presets: Sequence[M.RecipePreset] = (),
        secretary_key: str = "",
    ) -> None:
        super().__init__()
        self.recipe_presets = list(presets)
        self.secretary_key = secretary_key
        self.has_sec = False  # the secretary is only changed together with the recipe after a preset has been applied
        self.sec_value: Any = None
        self.field = field
        self.title_text = title
        self.specs = list(specs)
        self.as_list = as_list
        # stored in spec order: (first wheel, has sign, digits). The wheels themselves are laid out in screen order.
        self.groups: list[tuple[int, bool, int]] = [(0, False, 1)] * len(self.specs)

    def compose(self) -> ComposeResult:
        wheels: list[Wheel] = []
        order = sorted(
            range(len(self.specs)), key=lambda i: (self.specs[i].row, self.specs[i].col)
        )
        for gi in order:
            spec = self.specs[gi]
            signed, places = M.number_layout(
                spec.lo, spec.hi, spec.value, spec.min_places
            )
            start = len(wheels)
            value = M.clamp_number(spec.value, spec.lo, spec.hi)
            span = places + (1 if signed else 0)
            group_gap = (
                5 if spec.col > 0 else 0
            )  # leave a wider gap and draw a divider between the right group and the left group
            common = dict(span=span, row=spec.row, color=spec.color, tight=True)
            if signed:
                wheels.append(
                    Wheel(
                        ["+", "-"],
                        1 if value < 0 else 0,
                        label=spec.label,
                        gap=group_gap,
                        divider=group_gap > 0,
                        **common,
                    )
                )
            for pos, d in enumerate(M.digits_of(value, places)):
                first = pos == 0 and not signed
                wheels.append(
                    Wheel(
                        [str(n) for n in range(10)],
                        d,
                        label=spec.label if first else "",
                        gap=group_gap if first else 0,
                        divider=first and group_gap > 0,
                        **common,
                    )
                )
            self.groups[gi] = (start, signed, places)
        f = self.field
        with Vertical(classes="dlg dlg-wide"):
            yield from self.header(self.title_text, f.help)
            yield _static(self.meta_text(), classes="dlg-meta")
            with Horizontal(id="wheelrow"):
                if self.recipe_presets:
                    with Vertical(id="presetbox"):
                        yield _static(
                            t("Presets   (← / ↑ / p = here · Enter = apply)"),
                            classes="dlg-meta",
                        )
                        yield PickList(
                            [Row(M.recipe_preset_row(p)) for p in self.recipe_presets],
                            max_visible=8,
                            id="presets",
                        )
                        yield _static("", classes="dlg-meta", id="pcomment")
                yield WheelPicker(
                    wheels,
                    id="wheels",
                    grouped=self.grouped,
                    buttons=("OK", "Cancel") if self.grouped else (),
                )
            yield _static("", classes="dlg-preview", id="preview")
            yield _static("", classes="dlg-err", id="err")
            yield _static(
                t(self.HINT_GROUP if self.grouped else self.HINT),
                classes="dlg-meta",
                id="hint",
            )
            if not self.grouped:  # in grouped mode OK / Cancel are below the wheels and can be chosen with the arrow keys
                yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def meta_text(self) -> str:
        f = self.field
        return t(
            "{key}   {type}   default {default}",
            key=f.key,
            type=M.type_label(f),
            default=M.format_value(f, f.default, 30),
        )

    @property
    def grouped(self) -> bool:
        return self.as_list and len(self.specs) > 1

    def on_resize(self, event) -> None:
        Dialog.on_resize(self, event)
        picker = self.query_one(WheelPicker)
        overhead = self.OVERHEAD
        if self.recipe_presets:
            # enough room → presets go left of the wheels; otherwise stack above the wheels
            stacked = self.stacked = event.size.width < self.SIDE_BY_SIDE
            self.query_one("#wheelrow").set_class(stacked, "stack")
            lst = self.query_one("#presets", PickList)
            if stacked:
                overhead += self.PRESET_ROWS
                lst.max_visible = max(3, min(4, event.size.height - 22))
            else:
                lst.max_visible = max(3, min(8, event.size.height - 18))
            lst.set_rows(lst.rows, lst.cursor)
        picker.set_visible(
            5 if event.size.height - overhead >= picker.height_for(5) else 3
        )

    # --- preset ------------------------------------------------------------ #
    def action_focus_presets(self) -> None:
        if self.recipe_presets and not self.query_one(WheelPicker).in_digits:
            lst = self.query_one("#presets", PickList)
            lst.focus()
            self._show_comment(lst.cursor)

    def action_from_presets(self) -> None:
        """With presets on the left, → in the list returns to the wheels (ignored otherwise)."""
        if (
            self.recipe_presets
            and not self.stacked
            and self.query_one("#presets").has_focus
        ):
            self.query_one(WheelPicker).focus()

    def on_wheel_picker_leave(self, event: WheelPicker.Leave) -> None:
        """Wheel first level walked past the edge: side by side, ← goes to the preset list; stacked, ↑ goes to the preset list."""
        event.stop()
        if not self.recipe_presets:
            return
        if (event.direction == "left" and not self.stacked) or (
            event.direction == "up" and self.stacked
        ):
            self.action_focus_presets()

    def _show_comment(self, index: int) -> None:
        if 0 <= index < len(self.recipe_presets):
            self.query_one("#pcomment", Static).update(
                Text(self.recipe_presets[index].comment, style=DIM)
            )

    def on_pick_list_moved(self, event: PickList.Moved) -> None:
        event.stop()
        self._show_comment(event.index)

    def on_pick_list_edge(self, event: PickList.Edge) -> None:
        event.stop()
        event.prevent_default()  # do not pass this on to Dialog's "jump to buttons"
        if (
            self.stacked and event.direction > 0
        ):  # when stacked the list is above: ↓ at the end → wheels
            self.query_one(WheelPicker).focus()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        self._apply_preset(self.recipe_presets[event.index])
        self.query_one(WheelPicker).focus()

    def _apply_preset(self, preset: M.RecipePreset) -> None:
        for gi, value in enumerate(preset.recipe):
            spec = self.specs[gi]
            self._write(gi, M.clamp_number(value, spec.lo, spec.hi))
        if preset.secretary is not None and self.secretary_key:
            self.has_sec, self.sec_value = True, preset.secretary
        self._show_comment(self.recipe_presets.index(preset))
        self._update_preview()

    def action_cancel(self) -> None:
        """Esc: at the second level (adjusting a number) = discard this group's change and go back to choosing a resource; at the first level = cancel the whole dialog."""
        picker = self.query_one(WheelPicker)
        if picker.in_digits:
            picker.leave_digits(revert=True)
            self._update_preview()
            return
        super().action_cancel()

    def on_wheel_picker_level_changed(self, event: WheelPicker.LevelChanged) -> None:
        event.stop()
        self.query_one("#hint", Static).update(
            Text(
                t(self.HINT_DIGIT if event.level == "digit" else self.HINT_GROUP),
                style=DIM,
            )
        )

    def on_wheel_picker_cancelled(self, event: WheelPicker.Cancelled) -> None:
        event.stop()
        self.dismiss(None)

    def on_mount(self) -> None:
        self.query_one(WheelPicker).focus()
        self._update_preview()

    # --- read / write wheels ----------------------------------------------- #
    def _read(self, gi: int) -> int:
        picker = self.query_one(WheelPicker)
        start, signed, places = self.groups[gi]
        negative = False
        if signed:
            negative = picker.wheels[start].items[picker.wheels[start].index] == "-"
            start += 1
        digits = [
            int(picker.wheels[start + i].items[picker.wheels[start + i].index])
            for i in range(places)
        ]
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
                rng = t(
                    "   (range {lo} .. {hi})",
                    lo=spec.lo if spec.lo is not None else "…",
                    hi=spec.hi if spec.hi is not None else "…",
                )
            shown = f"= {values[0]}{rng}"
        if self.has_sec:
            shown += t("   secretary {value}", value=self.sec_value)
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


class TimeDialog(NumberDialog):
    """Hour : minute wheels, returns [hh, mm]."""

    def meta_text(self) -> str:
        return t("kcauto stops at this time of day (24-hour clock)")

    def _finish(self) -> None:
        self.accept(self._values())


# ---------------------------------------------------------------------- #
class SchedulerDialog(Dialog):
    """Schedule: only two rules — what time to stop kcauto, and after how many sorties to stop combat.

    The format written to the config file is fixed: ``time:HHMM:stop:kcauto`` and ``sorties_run:N:stop:combat``.
    Space / click = on/off, Enter = set value, o = OK. Other rules are not kept.
    """

    DEFAULTS = (("0300", "time"), 10)
    BINDINGS = [
        *Dialog.BINDINGS,
        Binding("o", "apply", show=False),
    ]

    def __init__(self, field: Field, items: Sequence[Any]) -> None:
        super().__init__()
        self.field = field
        self.sched_on = [False, False]
        self.sched_val: list[Any] = ["0300", 10]
        self.n_other = 0
        for item in items:
            try:
                rule = parse_rule(item)
            except ValueError:
                self.n_other += 1
                continue
            if (
                (rule.condition, rule.action, rule.module) == ("time", "stop", "kcauto")
                and re.fullmatch(r"\d{4}", rule.value)
                and not self.sched_on[0]
            ):
                self.sched_on[0], self.sched_val[0] = True, rule.value
            elif (
                (rule.condition, rule.action, rule.module)
                == ("sorties_run", "stop", "combat")
                and rule.value.isdigit()
                and not self.sched_on[1]
            ):
                self.sched_on[1], self.sched_val[1] = True, int(rule.value)
            else:
                self.n_other += 1

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg"):
            yield from self.header(self.field.label, self.field.help)
            yield PickList(self._build_rows(), max_visible=2, id="sched")
            note = ""
            if self.n_other:
                note = t(
                    "{n} other rule(s) in the file will be removed when you press OK.",
                    n=self.n_other,
                )
            yield _static(note, classes="dlg-err", id="err")
            yield _static(
                t("Space = on/off · Enter = set value · o = OK · Esc = cancel"),
                classes="dlg-meta",
            )
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def _build_rows(self) -> list[Row]:
        hhmm = self.sched_val[0]
        shown_t = f"{hhmm[:2]}:{hhmm[2:]}" if self.sched_on[0] else "--:--"
        shown_n = f"{self.sched_val[1]}" if self.sched_on[1] else "--"
        return [
            Row(
                M.pad_cells(t("Stop kcauto at"), 24) + shown_t,
                checked=self.sched_on[0],
                toggle=True,
            ),
            Row(
                M.pad_cells(t("Stop combat after"), 24) + t("{n} sortie(s)", n=shown_n),
                checked=self.sched_on[1],
                toggle=True,
            ),
        ]

    def _redraw(self) -> None:
        lst = self.query_one("#sched", PickList)
        lst.set_rows(self._build_rows(), lst.cursor)

    def on_mount(self) -> None:
        self.query_one("#sched", PickList).focus()

    def on_pick_list_toggled(self, event: PickList.Toggled) -> None:
        event.stop()
        self.sched_on[event.index] = not self.sched_on[event.index]
        self._redraw()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        i = event.index
        if i == 0:
            hh, mm = int(self.sched_val[0][:2]), int(self.sched_val[0][2:])
            specs = [
                NumSpec("hour", hh, 0, 23, min_places=2, row=0, col=0),
                NumSpec("min", mm, 0, 59, min_places=2, row=0, col=1),
            ]
            f = Field(
                "scheduler.time",
                Kind.RECIPE,
                [0, 0],
                t("Stop kcauto at"),
                t("Time of day when kcauto stops."),
            )
            self.app.push_screen(
                TimeDialog(f, t("Stop kcauto at"), specs, as_list=True),
                partial(self._value_set, 0),
            )
        else:
            spec = NumSpec("sorties", int(self.sched_val[1]), 1, 999)
            f = Field(
                "scheduler.sorties_run",
                Kind.INT,
                10,
                t("Stop combat after"),
                t("Combat stops after this many sorties."),
                min=1,
                max=999,
            )
            self.app.push_screen(
                NumberDialog(
                    f, t("Stop combat after (sorties)"), [spec], as_list=False
                ),
                partial(self._value_set, 1),
            )

    def _value_set(self, i: int, result: Optional[Picked]) -> None:
        if result is None:
            return
        if i == 0:
            hh, mm = result.value
            self.sched_val[0] = f"{hh:02d}{mm:02d}"
        else:
            self.sched_val[1] = int(result.value)
        self.sched_on[i] = True
        self._redraw()

    def _rules(self) -> list[str]:
        rules = []
        if self.sched_on[0]:
            rules.append(f"time:{self.sched_val[0]}:stop:kcauto")
        if self.sched_on[1]:
            rules.append(f"sorties_run:{self.sched_val[1]}:stop:combat")
        return rules

    def action_apply(self) -> None:
        self.accept(self._rules())

    def run_command(self, command: str) -> None:
        if command == "ok":
            self.action_apply()
        else:
            super().run_command(command)


class SecretaryDialog(Dialog):
    """Secretary ship: pick a ship type (DD, CV, ...) or enter a specific ship's production ID with the wheel."""

    FIT = {"ships": (11, 10)}

    def __init__(self, field: Field, current: Any) -> None:
        super().__init__()
        self.field = field
        self.current = current
        # (display text, ship type code or None = production ID, current value?)
        self.entries: list[tuple[str, Optional[str]]] = []
        for code, name in M.SHIP_TYPES:
            self.entries.append((M.pad_cells(code, 5) + t(name), code))
        self.entries.append((t("Production ID…"), None))
        self.extra: Optional[str] = None
        if isinstance(current, str) and current not in M.SHIP_TYPE_CODES:
            self.extra = current  # a non-standard string in the config file is still kept and selectable
            self.entries.insert(0, (M.pad_cells(current, 5) + t("(current)"), current))

    def _is_current(self, code: Optional[str]) -> bool:
        if code is None:
            return isinstance(self.current, int) and not isinstance(self.current, bool)
        return self.current == code

    def _rows(self) -> list[Row]:
        rows = []
        for text, code in self.entries:
            if code is None and self._is_current(None):
                text = t("Production ID…   now {value}", value=self.current)
            rows.append(Row(("● " if self._is_current(code) else "  ") + text))
        return rows

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg"):
            yield from self.header(self.field.label, self.field.help)
            yield PickList(self._rows(), max_visible=10, id="ships")
            yield _static(
                t("Enter / click = select · Esc = cancel"), classes="dlg-meta"
            )
            yield self.buttons(("Cancel", "cancel"))

    def on_mount(self) -> None:
        lst = self.query_one("#ships", PickList)
        for i, (_, code) in enumerate(self.entries):
            if self._is_current(code):
                lst.set_rows(lst.rows, i)
                break
        lst.focus()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        code = self.entries[event.index][1]
        if code is not None:
            self.accept(code)
            return
        start = self.current if self._is_current(None) else 0
        spec = NumSpec(
            t("production ID"), int(start), 0, M.SECRETARY_ID_MAX, min_places=5
        )
        f = Field(
            self.field.key,
            Kind.INT,
            0,
            self.field.label,
            t("Production ID of the ship to use as secretary."),
            min=0,
            max=M.SECRETARY_ID_MAX,
        )
        self.app.push_screen(
            NumberDialog(f, t("Production ID"), [spec], as_list=False), self._id_done
        )

    def _id_done(self, result: Optional[Picked]) -> None:
        if result is not None:
            self.accept(int(result.value))


class PresetWheelDialog(Dialog):
    """Fleet preset: a single-value scrolling list (auto first, then 1-15).

    The list field (combat.fleet_presets) always writes exactly one element; the trailing none = empty list.
    For pvp the trailing entries are 0 (unspecified) and null.
    """

    HINT = "↑ ↓  scroll    Enter  OK    Esc  cancel"

    def __init__(self, field: Field, value: Any) -> None:
        super().__init__()
        self.field = field
        self.value = value

    def compose(self) -> ComposeResult:
        f = self.field
        tokens = M.preset_wheel_tokens(f)
        current = M.preset_wheel_current(f, self.value)
        with Vertical(classes="dlg"):
            yield from self.header(f.label, f.help)
            yield WheelPicker(
                [Wheel(tokens, tokens.index(current), label="preset", wrap=False)],
                id="wheels",
            )
            yield _static("", classes="dlg-preview", id="preview")
            yield _static("", classes="dlg-meta", id="note")
            yield _static("", classes="dlg-err", id="err")
            yield _static(t(self.HINT), classes="dlg-meta")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def on_resize(self, event) -> None:
        Dialog.on_resize(self, event)
        picker = self.query_one(WheelPicker)
        picker.set_visible(5 if event.size.height - 15 >= picker.height_for(5) else 3)

    def on_mount(self) -> None:
        self.query_one(WheelPicker).focus()
        self._update_preview()
        if isinstance(self.value, list) and len(self.value) > 1:
            shown = ", ".join(str(v) for v in self.value)
            self.query_one("#note", Static).update(
                Text(
                    t(
                        "Currently {n} presets ({shown}); only one can be kept.",
                        n=len(self.value),
                        shown=shown,
                    ),
                    style="#e5c07b",
                )
            )

    def _token(self) -> str:
        return self.query_one(WheelPicker).values()[0]

    def _result(self) -> Any:
        return M.preset_wheel_result(self.field, self._token(), self.value)

    def on_wheel_picker_changed(self, event: WheelPicker.Changed) -> None:
        event.stop()
        self._update_preview()

    def _update_preview(self) -> None:
        shown = M.format_value(self.field, self._result(), 30)
        self.query_one("#preview", Static).update(
            Text("= " + shown, style="bold #e5c07b")
        )

    def on_wheel_picker_accepted(self, event: WheelPicker.Accepted) -> None:
        event.stop()
        self._finish()

    def _finish(self) -> None:
        value = self._result()
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
    """Sortie map: three wheels for world / map number / target node (the last two are ignored for auto).

    Target nodes only offer options that "really have a matching preset" in noro6, e.g. 2-2 has B-2-2-A, so ``2-2-A`` can be picked; "—" means no node specified (``2-2``).
    """

    HINT = "← →  world / map / node    ↑ ↓  scroll    Enter  OK    Esc  cancel"

    def __init__(
        self, field: Field, value: Any, nodes: Optional[M.NodeIndex] = None
    ) -> None:
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
        node_items = M.map_node_items(
            self.node_index, self.world, shown_number, self.node
        )
        node_index = node_items.index(self.node) if self.node in node_items else 0
        wheels = [
            Wheel(worlds, worlds.index(self.world), label="world", wrap=False),
            Wheel(
                numbers,
                min(number_index, len(numbers) - 1),
                label="map",
                wrap=False,
                gap=2,
            ),
            Wheel(node_items, node_index, label="node", wrap=False, gap=2),
        ]
        with Vertical(classes="dlg"):
            yield from self.header(f.label, f.help)
            yield WheelPicker(wheels, id="wheels")
            yield _static("", classes="dlg-preview", id="preview")
            yield _static("", classes="dlg-meta", id="note")
            yield _static("", classes="dlg-err", id="err")
            yield _static(t(self.HINT), classes="dlg-meta")
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
        if event.column == 0:  # changing the world changes the map number range
            world = picker.wheels[0].items[picker.wheels[0].index]
            old = picker.wheels[1]
            keep = old.index if old.items != ["—"] else 0
            picker.set_wheel(1, M.map_number_items(world), keep)
        if event.column in (
            0,
            1,
        ):  # changing the world or map number recomputes the node options
            world, number, _ = picker.values()
            picker.set_wheel(2, M.map_node_items(self.node_index, world, number), 0)
        self._update_preview()

    def _update_preview(self) -> None:
        picker = self.query_one(WheelPicker)
        world, number, node = picker.values()
        self.query_one("#preview", Static).update(
            Text("= " + self._current(), style="bold #e5c07b")
        )
        options = [n for n in picker.wheels[2].items if n != M.NO_NODE]
        if world == "auto":
            note = ""
        elif options:
            note = t("noro6 node presets for this map: ") + ", ".join(options)
        else:
            note = t("No node-specific noro6 preset for this map.")
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
    """Quest checklist grouped by prefix (events first). A group header = fold / unfold; Space ticks a quest, Enter confirms."""

    FIT = {"quests": (14, 14)}

    def __init__(
        self, field: Field, selected: Sequence[Any], catalog: Sequence[M.QuestInfo]
    ) -> None:
        super().__init__()
        self.field = field
        self.old = list(selected)
        self.chosen: set[str] = {str(s) for s in selected}
        self.groups = M.group_quests(catalog, selected)
        self.notes = {q.id: q.note for q in catalog}
        self._row_ids: list[
            tuple[str, Optional[str]]
        ] = []  # (group, quest ID or None = header)
        self.collapsed: set[str] = {g for g, _ in self.groups}  # all folded by default

    BINDINGS = [
        *Dialog.BINDINGS,
        Binding("a", "group(1)", show=False),
        Binding("n", "group(0)", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg"):
            yield from self.header(self.field.label, self.field.help)
            yield _static(
                t(
                    "Enter/click header = fold · Space = tick · a / n = all / none in group"
                ),
                classes="dlg-meta",
            )
            yield PickList(self._build_rows(), max_visible=14, id="quests")
            yield _static("", classes="dlg-meta", id="count")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def _build_rows(self) -> list[Row]:
        rows, self._row_ids = [], []
        for group, ids in self.groups:
            n = sum(1 for i in ids if i in self.chosen)
            fold = "▸" if group in self.collapsed else "▾"
            rows.append(
                Row(
                    f"{fold} {M.quest_group_title(group)}  ({n}/{len(ids)})",
                    toggle=True,
                    style="bold #e5c07b",
                )
            )
            self._row_ids.append((group, None))
            if group in self.collapsed:
                continue
            for qid in ids:
                note = self.notes.get(qid, "")
                rows.append(
                    Row(
                        f"{qid:<8} {note}".rstrip(),
                        checked=qid in self.chosen,
                        toggle=True,
                    )
                )
                self._row_ids.append((group, qid))
        return rows

    def _redraw(self) -> None:
        lst = self.query_one("#quests", PickList)
        lst.set_rows(self._build_rows(), lst.cursor)
        self.query_one("#count", Static).update(
            Text(t("{n} selected", n=len(self.chosen)), style=DIM)
        )

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
            self._fold(group)
            return
        elif qid in self.chosen:
            self.chosen.discard(qid)
        else:
            self.chosen.add(qid)
        self._redraw()

    def _fold(self, group: str) -> None:
        self.collapsed.symmetric_difference_update({group})
        self._redraw()

    def action_group(self, on: int) -> None:
        lst = self.query_one("#quests", PickList)
        if 0 <= lst.cursor < len(self._row_ids):
            self._set_group(self._row_ids[lst.cursor][0], bool(on))
            self._redraw()

    def on_pick_list_chosen(self, event: PickList.Chosen) -> None:
        event.stop()
        group, qid = self._row_ids[event.index]
        if qid is None:
            self._fold(group)
        else:
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
    """JSON editor (ship_switcher.slots, unknown keys). Ctrl+S or click OK to apply."""

    BINDINGS = [*Dialog.BINDINGS, Binding("ctrl+s", "apply", show=False)]

    def __init__(
        self, title: str, help_text: str, value: Any, *, want_object: bool
    ) -> None:
        super().__init__()
        self.title_text, self.help_text = title, help_text
        self.value = value
        self.want_object = want_object

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg dlg-wide"):
            yield from self.header(self.title_text, self.help_text)
            if TextArea is not None:
                yield TextArea(M.dump_json(self.value), id="json")
            else:  # pragma: no cover
                import json

                yield Input(value=json.dumps(self.value, ensure_ascii=False), id="json")
            yield _static("", classes="dlg-err", id="err")
            yield _static(t("Ctrl+S = apply · Esc = cancel"), classes="dlg-meta")
            yield self.buttons(("OK", "ok"), ("Cancel", "cancel"))

    def on_mount(self) -> None:
        self.query_one("#json").focus()
        self._check()

    def _text(self) -> str:
        widget = self.query_one("#json")
        return (
            widget.text
            if TextArea is not None and isinstance(widget, TextArea)
            else widget.value
        )

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

    def on_input_changed(self, event: Input.Changed) -> None:  # pragma: no cover
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
    """Single-line text input (strings, decimals, key names). parse(text) → (value, error message)."""

    def __init__(
        self,
        title: str,
        help_text: str,
        initial: str,
        parse: Callable[[str], tuple[Any, str]],
    ) -> None:
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
    "str": "text",
    "int": "whole number (wheel)",
    "float": "decimal number",
    "bool": "on / off",
    "null": "empty value",
    "object": "group of named items { }",
    "list": "ordered list [ ]",
}


class NewItemDialog(Dialog):
    """Add a tree item: under an object enter a key first, then pick a type; under a list only pick a type."""

    FIT = {"kinds": (13, 7)}

    def __init__(self, needs_key: bool, existing: Sequence[Any]) -> None:
        super().__init__()
        self.needs_key = needs_key
        self.existing = list(existing)

    def compose(self) -> ComposeResult:
        with Vertical(classes="dlg"):
            yield _static(
                t("Add item") if self.needs_key else t("Add list item"),
                classes="dlg-title",
            )
            if self.needs_key:
                yield Input(placeholder=t("key name, then Enter"), id="key")
            rows = [Row(f"{k:<7} {t(_KIND_HELP[k])}") for k in TR.KINDS]
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
    """Tree-table editor for JSON: expand / collapse, add, rename, delete, change type; numbers use wheels.

    For settings whose structure is not fixed (ship_switcher.slots, unknown keys). Use the dedicated control for fields with a known structure.
    """

    FIT = {"tree": (15, 12)}
    HINT = (
        "↑↓ move  →← open/close  Enter edit  a add  x remove  r rename  t type  "
        "j raw JSON  Ctrl+S apply  Esc cancel"
    )

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

    def __init__(
        self, title: str, help_text: str, value: Any, *, field: Optional[Field] = None
    ) -> None:
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
            yield PickList(
                [], max_visible=12, empty=t("(empty)  —  press a to add"), id="tree"
            )
            yield _static("", classes="dlg-err", id="err")
            yield _static(t(self.HINT), classes="dlg-meta")
            yield self.buttons(
                ("OK", "ok"), ("Add", "add"), ("Remove", "remove"), ("Cancel", "cancel")
            )

    def on_mount(self) -> None:
        self._rebuild()
        self.query_one("#tree", PickList).focus()

    # --- table -------------------------------------------------------------- #
    def _tree(self) -> PickList:
        return self.query_one("#tree", PickList)

    def _selected(self) -> Optional[TR.TreeRow]:
        lst = self._tree()
        return (
            self.flat[lst.cursor]
            if self.flat and 0 <= lst.cursor < len(self.flat)
            else None
        )

    def _rebuild(self, select: Optional[TR.Path] = None) -> None:
        lst = self._tree()
        keep = lst.cursor
        self.flat = TR.flatten(self.doc, self.expanded)
        width = max(lst.size.width, 30)
        key_w = TR.key_column_width(self.flat, width)
        rows = [
            Row(TR.row_text(r, key_w, width), toggle=r.expandable or r.kind == "bool")
            for r in self.flat
        ]
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

    def on_pick_list_moved(
        self, event
    ) -> None:  # reserved: update the path when the cursor moves
        self._update_crumb()

    # --- expand / collapse -------------------------------------------------- #
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
        elif len(row.path) > 1:  # back to the parent level
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
        """Enter: container = expand / collapse; bool = toggle; anything else = open the editor."""
        if row.expandable:
            self._toggle_open(row)
        elif row.kind == "bool":
            TR.set_at(self.doc, row.path, not row.value)
            self._rebuild(row.path)
        else:
            self._edit(row)

    # --- edit value ---------------------------------------------------------- #
    def _edit(self, row: TR.TreeRow) -> None:
        label = TR.path_text(row.path)
        done = partial(self._edited, row.path)
        if row.kind == "int":
            limit = max(9_999_999, 10 ** len(str(abs(row.value))) - 1)
            field = Field(label, Kind.INT, 0, label, "", min=-limit, max=limit)
            self.app.push_screen(
                NumberDialog(
                    field,
                    label,
                    [NumSpec("value", row.value, -limit, limit)],
                    as_list=False,
                ),
                done,
            )
        elif row.kind == "float":
            self.app.push_screen(
                ValueDialog(label, t("Decimal number"), repr(row.value), _parse_float),
                done,
            )
        elif row.kind == "str":
            self.app.push_screen(
                ValueDialog(label, t("Text"), row.value, lambda text: (text, "")), done
            )
        else:  # null → pick a type
            self.action_retype()

    def _edited(self, path: TR.Path, result: Optional[Picked]) -> None:
        if result is not None:
            TR.set_at(self.doc, path, result.value)
            self._rebuild(path)

    # --- add / delete / rename / change type ------------------------------- #
    def _container_target(self) -> TR.Path:
        row = self._selected()
        if row is None:
            return ()
        return row.path if row.expandable else TR.parent_path(row.path)

    def action_add(self) -> None:
        target = self._container_target()
        container = TR.get_at(self.doc, target)
        self.app.push_screen(
            NewItemDialog(
                isinstance(container, dict),
                list(container) if isinstance(container, dict) else [],
            ),
            partial(self._added, target),
        )

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
            self._edit(row)  # after adding, type the content straight away

    def action_remove(self) -> None:
        row = self._selected()
        if row is None:
            return
        TR.delete_at(self.doc, row.path)
        self.expanded = {p for p in self.expanded if p[: len(row.path)] != row.path}
        self._rebuild()

    def action_rename(self) -> None:
        row = self._selected()
        if row is None or not isinstance(row.key, str):
            return
        parent = TR.get_at(self.doc, TR.parent_path(row.path))

        def parse(text: str) -> tuple[Any, str]:
            return text.strip(), TR.key_error(parent, text.strip(), row.key) or ""

        self.app.push_screen(
            ValueDialog(t("Rename key"), TR.path_text(row.path), row.key, parse),
            partial(self._renamed, row),
        )

    def _renamed(self, row: TR.TreeRow, result: Optional[Picked]) -> None:
        if result is None or result.value == row.key:
            return
        new_path = TR.rename_key(self.doc, row.path, result.value)
        self.expanded = {
            new_path + p[len(row.path) :] if p[: len(row.path)] == row.path else p
            for p in self.expanded
        }
        self._rebuild(new_path)

    def action_retype(self) -> None:
        row = self._selected()
        if row is None:
            return
        options = [(f"{k:<7} {t(_KIND_HELP[k])}", k) for k in TR.KINDS]
        self.app.push_screen(
            ChoiceDialog(
                t("Change type"),
                t(
                    "Content is kept when it converts cleanly "
                    '("12" → 12); otherwise the new type starts empty.'
                ),
                options,
                row.kind,
            ),
            partial(self._retyped, row),
        )

    def _retyped(self, row: TR.TreeRow, result: Optional[Picked]) -> None:
        if result is None or result.value == row.kind:
            return
        TR.set_at(self.doc, row.path, TR.convert(row.value, result.value))
        self._rebuild(row.path)

    # --- raw JSON / apply ---------------------------------------------------- #
    def action_raw_json(self) -> None:
        self.app.push_screen(
            JsonDialog(
                self.title_text,
                t("Raw JSON"),
                self.doc,
                want_object=isinstance(self.doc, dict),
            ),
            self._raw_done,
        )

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
            self.show_error(t("Top level must stay a {kind}", kind=self.root_kind))
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
        return None, t("Enter a number such as 1.5")


# ---------------------------------------------------------------------- #
class DangerDialog(Dialog):
    """Second confirmation for high-risk settings. y / n."""

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
        body.append(t("⚠ Dangerous setting") + "\n", style="bold #e06c75")
        body.append(f"{self.field.label}\n", style="bold")
        body.append(self.field.help + "\n\n")
        if self.added:
            body.append(
                t("Adding: ") + ", ".join(str(a) for a in self.added) + "\n\n",
                style="#e5c07b",
            )
        body.append(t("Apply this change?"))
        with Vertical(classes="dlg dlg-danger"):
            yield Static(body)
            yield Horizontal(
                ActionLabel("Apply", "yes", hotkey="y"),
                ActionLabel("Cancel", "no", hotkey="n"),
                classes="dlg-buttons",
            )

    def action_answer(self, yes: int) -> None:
        self.dismiss(bool(yes))

    def run_command(self, command: str) -> None:
        self.dismiss(command == "yes")


# ---------------------------------------------------------------------- #
class SearchDialog(Dialog):
    """/ searches all fields. ↑↓ select, Enter jumps there."""

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
            yield _static(t("Search settings"), classes="dlg-title")
            yield Input(placeholder=t("key, label or description…"), id="q")
            yield PickList([], max_visible=12, empty=t("type to search"), id="hits")
            yield _static(t("↑↓ select · Enter jump · Esc close"), classes="dlg-meta")

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
                    rows.append(Row(M.pad_cells(key, 34) + t(" (unknown key)")))
        lst = self.query_one("#hits", PickList)
        lst.empty = t("no match") if query else t("type to search")
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
