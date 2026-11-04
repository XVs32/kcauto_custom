"""Full-screen editor (btop Options style).

   ┌ modules ┐┌ combat ─────────────────────────────┐
   │ ● combat ││ ── Basic ──                         │
   │ ○ exped… ││ * Enable combat          on         │
   │ …        ││   Sortie map             1-1        │
   └─────────┘└─────────────────────────────────────┘
   ┌ combat.sortie_map ─ help / type / default / issues ┐

Every change is written to the ConfigStore immediately (the dashboard updates in sync); saving is decided by w.
"""

from __future__ import annotations

from functools import partial
from typing import Any, Callable, Optional

from rich.text import Text
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Static

from .. import akashi, keymap
from ..i18n import t
from ..modules import CARD_BY_MODULE, split_hotkey
from ..schema import (
    OVERRIDE_KEY,
    SCHEMA,
    Field,
    Kind,
    fields_of,
    groups_of,
    ignored_by_override,
)
from ..layout import fit_segments
from ..store import ConfigStore
from . import model as M
from . import narrow as N
from . import noro6
from .dialogs import (
    ChoiceDialog,
    DangerDialog,
    JsonDialog,
    ListDialog,
    MapDialog,
    NumberDialog,
    SchedulerDialog,
    NumSpec,
    Picked,
    SecretaryDialog,
    PresetDialog,
    PresetWheelDialog,
    QuestDialog,
    SearchDialog,
    TableDialog,
    TextDialog,
    TreeDialog,
)

FLAG_MARK = {
    "error": ("✖", "bold #e06c75"),
    "danger": ("!", "bold #c678dd"),
    "warning": ("⚠", "#e5c07b"),
    "": (" ", ""),
}
NARROW_WIDTH = N.NARROW_WIDTH

HINTS = N.EDITOR_HINTS


# ---------------------------------------------------------------------- #
_KEYS = keymap.active()  # loaded once at start-up (see keymap.py)


class ModuleList(Widget, can_focus=True):
    """Module list on the left. Up/Down switch module; Enter / Right enter the form.

    The first row is ``..`` (parent): selecting it with Enter or a click closes the editor,
    exactly like Esc. Moving the highlight onto it does not leave by itself.
    """

    BINDINGS = [
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("enter", "enter_form", show=False),
        Binding("right", "right_form", show=False),
    ]

    class Selected(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    class EnterForm(Message):
        pass

    class Back(Message):
        """The ``..`` row was selected."""

    def __init__(self, store: ConfigStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self.store = store
        self._index = 0
        self.at_parent = False  # highlight is on the ".." row
        self.styles.height = len(M.MODULE_ENTRIES) + 1

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int) -> None:
        self._index = value
        self.at_parent = False  # choosing a module always leaves the ".." row

    def action_move(self, delta: int) -> None:
        if self.at_parent:
            if delta > 0:
                self.at_parent = False
                self.refresh()
            return
        new = self._index + delta
        if new < 0:
            self.at_parent = True
            self.refresh()
            return
        new = min(new, len(M.MODULE_ENTRIES) - 1)
        if new != self._index:
            self.post_message(self.Selected(new))

    def action_enter_form(self) -> None:
        self.post_message(self.Back() if self.at_parent else self.EnterForm())

    def action_right_form(self) -> None:
        if not self.at_parent:
            self.post_message(self.EnterForm())

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.focus()
        if event.y == 0:
            self.post_message(self.Back())
        elif 1 <= event.y <= len(M.MODULE_ENTRIES):
            self.at_parent = False
            self.post_message(self.Selected(event.y - 1))
            if getattr(event, "chain", 1) >= 2:
                self.post_message(self.EnterForm())

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    def render(self) -> Text:
        values = self.store.as_dict()
        changed = self.store.changed_keys()
        issues = self.store.issues()
        width = max(self.size.width, 14)
        text = Text(no_wrap=True, overflow="crop")
        parent = Text(no_wrap=True)
        parent.append("▌" if self.at_parent else " ", style="#9aa0a6")
        parent.append("  ..", style="bold #9aa0a6")
        parent.pad_right(max(0, width - parent.cell_len))
        if self.at_parent:
            parent.stylize("on #3a4150" if self.has_focus else "on #242932")
        text.append_text(parent)
        text.append("\n")
        for i, entry in enumerate(M.MODULE_ENTRIES):
            keys = set(M.module_keys(entry.module, values))
            n_changed = sum(1 for k in changed if k in keys)
            has_error = any(x.level == "error" and keys & set(x.keys) for x in issues)

            selected = i == self._index and not self.at_parent
            bg = ("on #3a4150" if self.has_focus else "on #242932") if selected else ""
            line = Text(no_wrap=True)
            line.append("▌" if selected else " ", style=entry.color)
            spec = CARD_BY_MODULE.get(entry.module)
            if spec is not None and spec.toggleable:
                on_ = values.get(spec.enabled_key) is True
                line.append(
                    "● " if on_ else "○ ", style="#98c379" if on_ else "#6b7280"
                )
            else:
                line.append("  ")
            before, hot, after = split_hotkey(entry.label, entry.hotkey)
            line.append(before)
            line.append(hot, style="bold #e5c07b")
            line.append(after)
            tail = ""
            if has_error:
                tail += "✖"
            if n_changed:
                tail += f"{n_changed}*"
            if tail:
                gap = max(1, width - line.cell_len - len(tail) - 1)
                line.append(" " * gap)
                line.append(tail, style="bold #e06c75" if has_error else "bold #e5c07b")
            line.pad_right(max(0, width - line.cell_len))
            if bg:
                line.stylize(bg)
            text.append_text(line)
            if i < len(M.MODULE_ENTRIES) - 1:
                text.append("\n")
        return text


class ModuleTabs(Widget):
    """One-row switcher that replaces the module list on the left in narrow windows: ‹ previous  [ current ]  next ›.

    Click the left third = previous module, the right third = next; on the keyboard use [ ] or the module shortcuts.
    """

    class Step(Message):
        def __init__(self, delta: int) -> None:
            super().__init__()
            self.delta = delta

    ROLE_STYLE = {
        "arrow": "bold #e5c07b",
        "side": "#6b7280",
        "gap": "",
        "pos": "#6b7280",
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.index = 0

    def on_click(self, event: events.Click) -> None:
        event.stop()
        delta = N.tabs_step(event.x, max(self.size.width, 1))
        if delta:
            self.post_message(self.Step(delta))

    def render(self) -> Text:
        width = max(self.size.width, 20)
        labels = [e.label for e in M.MODULE_ENTRIES]
        segments = N.tabs_centered(labels, self.index, width)
        color = M.MODULE_ENTRIES[self.index].color
        text = Text(no_wrap=True, overflow="ellipsis")
        for piece, role in segments:
            style = f"bold {color}" if role == "current" else self.ROLE_STYLE[role]
            text.append(piece, style=style)
        return text


# ---------------------------------------------------------------------- #
class FieldRow(Widget, can_focus=True):
    """One row of the form: flag, modified mark, label, value. A single click edits."""

    class Activated(Message):
        """Clicking a non-adjustable field → open the editor."""

        def __init__(self, row: "FieldRow") -> None:
            super().__init__()
            self.row = row

    class EnterEdit(Message):
        """Clicking an already selected adjustable field once more → enter editing (same as Enter)."""

        def __init__(self, row: "FieldRow") -> None:
            super().__init__()
            self.row = row

    class Adjust(Message):
        """Clicking the ‹ › arrows while editing: delta = -1 / +1."""

        def __init__(self, row: "FieldRow", delta: int) -> None:
            super().__init__()
            self.row = row
            self.delta = delta

    def __init__(self, store: ConfigStore, key: str) -> None:
        super().__init__()
        self.store = store
        self.key = key
        self.field: Optional[Field] = SCHEMA.get(key)
        self.in_edit = False  # second level: the value of this row is being adjusted (only then are ‹ › drawn)
        self._zones = None  # clickable ranges of the arrows currently drawn on screen (None if not drawn)
        self._arrows_drawn = False
        self._focus_drawn = False
        self._arrows_at_down = False
        self._focused_at_down = False

    def on_mouse_down(self, event: events.MouseDown) -> None:
        # Focus is already set *before* the mouse press, so record "what the screen looked like at the time of the press" instead:
        # not selected at that time → this click only selects; already selected → it counts as "enter editing".
        self._arrows_at_down = self._arrows_drawn
        self._focused_at_down = self._focus_drawn

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.focus()
        if M.adjustable(self.field):
            if self.in_edit:
                if self._arrows_at_down and self._zones is not None:
                    hit = N.arrow_hit(self._zones, event.x, event.y)
                    if hit:
                        self.post_message(self.Adjust(self, hit))
                return
            if self._focused_at_down:
                self.post_message(self.EnterEdit(self))
            return  # the first click only selects: no value change, no dialog
        self.post_message(self.Activated(self))

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    def render(self) -> Text:
        width = max(self.size.width, 24)
        field = self.field
        value = self.store.get(self.key) if self.key in self.store else None
        flag = M.row_flag(self.store.issues_for(self.key))
        changed = self.store.is_changed(self.key)
        compact = self.size.height >= 2

        label_w, value_w = N.row_columns(width, compact)
        label = field.label if field else self.key
        ignored = ignored_by_override(self.key, self.store.get(OVERRIDE_KEY))
        forced = self.key == akashi.ENABLED_KEY and akashi.forced_off(
            self.store.as_dict()
        )
        ignored = ignored or forced
        dim = bool(field and field.advanced) or ignored
        adjustable = M.adjustable(field)
        arrows = adjustable and self.in_edit
        # every row reserves arrow space on both sides of the value so values line up vertically
        value_w = max(4, value_w - 2 * N.ARROW_SLOT)
        shown = (
            M.format_value(field, value, value_w)
            if field
            else M.format_raw(value, value_w)
        )

        mark, mark_style = FLAG_MARK[flag]
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(mark, style=mark_style)
        text.append("*" if changed else " ", style="bold #e5c07b")
        text.append(" ")
        if compact:  # narrow: label on one row, value on the next
            text.append(M.clip_cells(label, label_w), style="#6b7280" if dim else "")
            text.append("\n   ")
        else:
            text.append(M.pad_cells(label, label_w), style="#6b7280" if dim else "")
            text.append("  ")
        if adjustable:
            text.append(
                "‹ " if arrows else "  ", style=_arrow_style(field, value, -1, arrows)
            )
        else:
            text.append("  ")
        text.append(
            shown,
            style=("bold " if arrows else "")
            + (
                "#6b7280"
                if ignored and flag == ""
                else _value_style(value, flag, changed)
            ),
        )
        if arrows:
            text.append(" ›", style=_arrow_style(field, value, 1, True))
        self._arrows_drawn = arrows
        self._focus_drawn = self.has_focus
        self._zones = (
            N.arrow_zones(label_w, M.cell_len(shown), compact) if arrows else None
        )
        return text


def _arrow_style(field: Field, value: Any, direction: int, shown: bool) -> str:
    """Arrows that can still move in that direction are bright yellow; ones at the end are dim."""
    if not shown:
        return ""
    return "bold #e5c07b" if M.can_adjust(field, value, direction) else "#4b5263"


class BulkRow(FieldRow):
    """Virtual row for expeditions: "set fleets 2/3/4 at once"; does not correspond to any config key."""

    def __init__(self, store: ConfigStore) -> None:
        super().__init__(store, M.BULK_EXPEDITION)

    def render(self) -> Text:
        width = max(self.size.width, 24)
        compact = self.size.height >= 2
        label_w, value_w = N.row_columns(width, compact)
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append("   ")
        if compact:
            text.append(
                M.clip_cells(t("All fleets 2/3/4") + "  ▸", label_w),
                style="bold #56b6c2",
            )
            text.append("\n   ")
        else:
            text.append(
                M.pad_cells(t("All fleets 2/3/4") + "  ▸", label_w),
                style="bold #56b6c2",
            )
            text.append("  ")
        text.append(
            M.clip_cells(M.bulk_summary(self.store.as_dict()), value_w), style="#c8ccd4"
        )
        return text


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _value_style(value: Any, flag: str, changed: bool) -> str:
    if flag == "error":
        return "#e06c75"
    if value is True:
        return "#98c379"
    if value is False or value is None:
        return "#7f848e"
    return "#e5c07b" if changed else "#c8ccd4"


class FormPane(VerticalScroll, can_focus=False, inherit_bindings=False):
    """The form of one module (split into sections by group). All modules' panes exist at the same time; only the selected one is shown.

    VerticalScroll has built-in "scroll the view" bindings for ↑ ↓ PgUp PgDn Home End. These sit earlier in the widget chain than EditorScreen's "previous row / next row", so as soon as the content exceeds the screen height (a scrollbar appears) they steal the keys and the whole panel scrolls instead of the cursor moving.
    So the built-in bindings are not inherited; cursor movement is handled by EditorScreen, and the focused row scrolls into view automatically. The mouse wheel is unaffected.

    Note: it must be the class-declaration keyword argument inherit_bindings=False. Writing ``inherit_bindings = False`` inside the class body is just an ordinary attribute and Textual ignores it.
    """

    def __init__(self, store: ConfigStore, module: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.store = store
        self.module = module

    def compose(self) -> ComposeResult:
        if self.module == M.OTHER:
            keys = M.unknown_keys(self.store.as_dict())
            if not keys:
                yield Static(
                    Text(
                        t(
                            "No unknown keys. Settings kcauto adds in newer "
                            "versions show up here and are kept when saving."
                        ),
                        style="#6b7280",
                    ),
                    classes="grp",
                )
            for key in keys:
                yield FieldRow(self.store, key)
            return
        for group in groups_of(self.module):
            yield Static(
                Text(f"── {M.group_title(group)} ──", style="bold #7f848e"),
                classes="grp",
            )
            if self.module == "expedition" and group == "fleets":
                yield BulkRow(self.store)
            for field in fields_of(self.module):
                if field.group == group and field.key not in M.HIDDEN_KEYS:
                    yield FieldRow(self.store, field.key)


# ---------------------------------------------------------------------- #
class EditorScreen(Screen):
    BINDINGS = [
        Binding("escape", "close", "Back", show=False),
        Binding("up", "row(-1)", show=False),
        Binding("down", "row(1)", show=False),
        Binding("pageup", "row(-8)", show=False),
        Binding("pagedown", "row(8)", show=False),
        Binding("home", "row(-999)", show=False),
        Binding("end", "row(999)", show=False),
        Binding("left", "horizontal(-1)", show=False),
        Binding("right", "horizontal(1)", show=False),
        Binding(_KEYS.binding_key("editor.module_prev"), "module(-1)", show=False),
        Binding(_KEYS.binding_key("editor.module_next"), "module(1)", show=False),
        Binding("enter", "edit", show=False),
        Binding("space", "quick", show=False),
        Binding("plus,+,equals_sign,=", "adjust(1)", show=False),
        Binding("minus,-", "adjust(-1)", show=False),
        Binding(_KEYS.binding_key("editor.reset_default"), "reset_default", show=False),
        Binding(_KEYS.binding_key("editor.undo"), "undo", show=False),
        Binding(_KEYS.binding_key("editor.search"), "search", show=False),
        *(
            Binding(
                _KEYS.binding_key(f"module.{e.module}"),
                f"goto_module('{e.module}')",
                show=False,
            )
            for e in M.MODULE_ENTRIES
        ),
    ]

    def __init__(self, store: ConfigStore, module: str, *, root: str = ".") -> None:
        super().__init__()
        self.store = store
        self.project_root = root  # project root (used to find data/quests/quests.json)
        self._catalog: Optional[list[M.QuestInfo]] = None
        self._edit_row: Optional[FieldRow] = (
            None  # second level: the row being adjusted
        )
        self._edit_before: Any = (
            None  # value before editing started, used by Esc to restore it
        )
        self._noro6_cache: Optional[M.NodeIndex] = None
        names = [e.module for e in M.MODULE_ENTRIES]
        self.index = names.index(module) if module in names else 0

    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        yield Static(id="ed-top")
        yield ModuleTabs(id="ed-tabs")
        with Horizontal(id="ed-body"):
            with Vertical(id="ed-left"):
                yield ModuleList(self.store, id="ed-modules")
            with Vertical(id="ed-right"):
                for entry in M.MODULE_ENTRIES:
                    pane = FormPane(self.store, entry.module, id=f"pane-{entry.module}")
                    pane.display = False
                    yield pane
        yield Static(id="ed-help")
        yield Static(self._hints(0), id="ed-hints")

    @staticmethod
    def _hints(width: int, editing: bool = False) -> Text:
        """Bottom hints; on narrow windows the minor ones are dropped and enter / search / back are kept.
        While editing a row (second level) only ←→ change, Enter confirm and Esc cancel are shown.
        """
        hints = N.EDIT_HINTS if editing else HINTS
        lengths = [
            (desc, M.cell_len(key) + M.cell_len(t(desc)) + 3) for key, desc in hints
        ]
        kept = fit_segments(
            lengths,
            N.EDIT_HINT_DROP if editing else N.EDITOR_HINT_DROP,
            width - 1 if width else 0,
        )
        text = Text(no_wrap=True, overflow="ellipsis")
        for key, desc in hints:
            if desc in kept:
                text.append(key, style="bold #e5c07b")
                text.append(f" {t(desc)}  ", style="#9aa0a6")
        return text

    def on_mount(self) -> None:
        self.query_one("#ed-left").border_title = t("modules")
        self.store.subscribe(self._on_store_change)
        self.set_class(self.size.width < N.NARROW_WIDTH, "narrow")
        self.set_class(self.size.width < N.COMPACT_WIDTH, "compact")
        self._show_module(self.index)
        self.call_after_refresh(self._focus_first_row)

    def on_unmount(self) -> None:
        self.store.unsubscribe(self._on_store_change)

    def on_resize(self, event: events.Resize) -> None:
        width = event.size.width
        self.set_class(width < N.NARROW_WIDTH, "narrow")
        self.set_class(width < N.COMPACT_WIDTH, "compact")
        self._refresh_hints()
        self._refresh_top()

    # ------------------------------------------------------------------ #
    # module switching
    # ------------------------------------------------------------------ #
    @property
    def entry(self) -> M.ModuleEntry:
        return M.MODULE_ENTRIES[self.index]

    def _pane(self, module: str) -> FormPane:
        return self.query_one(f"#pane-{module}", FormPane)

    def _field_rows(self) -> list[FieldRow]:
        return list(self._pane(self.entry.module).query(FieldRow))

    def _show_module(self, index: int) -> None:
        self.index = index
        for e in M.MODULE_ENTRIES:
            self._pane(e.module).display = e.module == self.entry.module
        right = self.query_one("#ed-right")
        right.border_title = self.entry.label
        right.styles.border = ("round", self.entry.color)
        right.styles.border_title_color = self.entry.color
        modules = self.query_one(ModuleList)
        modules.index = index
        modules.refresh()
        tabs = self.query_one(ModuleTabs)
        tabs.index = index
        tabs.refresh()
        self._refresh_top()
        rows = self._field_rows()
        self._update_help(rows[0] if rows else None)

    def _focus_first_row(self) -> None:
        rows = self._field_rows()
        if rows:
            rows[0].focus()
            self._pane(self.entry.module).scroll_home(animate=False)

    @on(ModuleList.Selected)
    def _module_selected(self, event: ModuleList.Selected) -> None:
        self._show_module(event.index)

    @on(ModuleTabs.Step)
    def _tabs_step(self, event: ModuleTabs.Step) -> None:
        self.action_module(event.delta)

    @on(ModuleList.EnterForm)
    def _module_enter(self) -> None:
        self._focus_first_row()

    @on(ModuleList.Back)
    def _module_back(self) -> None:
        self.action_close()  # same as Esc

    def action_goto_module(self, module: str) -> None:
        if self._edit_row is not None:
            return  # while editing, press Enter to confirm or Esc to cancel first
        names = [e.module for e in M.MODULE_ENTRIES]
        self._show_module(names.index(module))
        self._focus_first_row()

    def action_module(self, delta: int) -> None:
        if self._edit_row is not None:
            return
        new = (self.index + delta) % len(M.MODULE_ENTRIES)
        self._show_module(new)
        if isinstance(self.focused, FieldRow):
            self._focus_first_row()

    def action_horizontal(self, direction: int) -> None:
        if self._edit_row is not None:  # second level: ← → change this row's value
            self._adjust_row(self._edit_row, direction)
            return
        if self.has_class("narrow"):
            self.action_module(direction)
        elif direction < 0:
            self.query_one(ModuleList).focus()

    # ------------------------------------------------------------------ #
    # row movement
    # ------------------------------------------------------------------ #
    def action_row(self, delta: int) -> None:
        if self._edit_row is not None:
            return  # second level: ↑ ↓ do not move, so you do not leave by accident
        rows = self._field_rows()
        if not rows:
            return
        focused = self.focused
        current = (
            rows.index(focused) if focused in rows else (-1 if delta > 0 else len(rows))
        )
        target = min(max(current + delta, 0), len(rows) - 1)
        rows[target].focus()
        if target == 0:
            self._pane(self.entry.module).scroll_home(animate=False)

    @on(events.DescendantFocus)
    def _focus_changed(self, event: events.DescendantFocus) -> None:
        if self._edit_row is not None and event.widget is not self._edit_row:
            self._end_edit(
                confirm=True
            )  # clicking elsewhere = confirm and leave editing
        if isinstance(event.widget, FieldRow):
            self._update_help(event.widget)

    # ------------------------------------------------------------------ #
    # info rows above and below
    # ------------------------------------------------------------------ #
    def _refresh_hints(self) -> None:
        self.query_one("#ed-hints", Static).update(
            self._hints(self.size.width, self._edit_row is not None)
        )

    def _refresh_top(self) -> None:
        issues = self.store.issues()
        errors = sum(1 for i in issues if i.level == "error")
        warnings = sum(1 for i in issues if i.level != "error")
        n = len(self.store.changed_keys())

        parts: list[tuple[str, Text]] = []

        def seg(name: str, piece: str, style: str) -> None:
            parts.append((name, Text(piece, style=style, no_wrap=True)))

        seg("badge", t(" Editor "), "bold #0f1115 on #e5c07b")
        seg("file", f"  {self.store.path.name}", "bold")
        if n:
            seg("dirty", "  " + t("{n} modified*", n=n), "bold #e5c07b")
        else:
            seg("dirty", "  " + t("saved"), "#6b7280")
        if errors:
            seg("errors", f"  ✖ {errors}", "bold #e06c75")
        if warnings:
            seg("warnings", f"  ⚠ {warnings}", "#e5c07b")

        kept = fit_segments(
            [(k, t.cell_len) for k, t in parts], N.TOP_DROP, self.size.width
        )
        text = Text(no_wrap=True, overflow="ellipsis")
        for name, piece in parts:
            if name in kept:
                text.append_text(piece)
        self.query_one("#ed-top", Static).update(text)

    def _update_help(self, row: Optional[FieldRow]) -> None:
        panel = self.query_one("#ed-help", Static)
        if row is None:
            panel.update(Text(t("(nothing here)"), style="#6b7280"))
            return
        key = row.key
        issues = self.store.issues_for(key)
        changed = self.store.is_changed(key)
        text = Text()
        if isinstance(row, BulkRow):
            text.append(t("All fleets 2/3/4") + "\n", style="bold")
            text.append(
                t(
                    "Set the expedition destinations of fleets 2, 3 and 4 in one go "
                    "(auto, overnight, a custom list, or clear)."
                )
                + "\n",
                style="#9aa0a6",
            )
            text.append(
                t("now: ") + M.bulk_summary(self.store.as_dict()), style="#9aa0a6"
            )
        elif row.field is None:
            text.append(key + "\n", style="bold")
            text.append(
                t("Unknown key — kept as-is when saving. Enter edits it as JSON.")
                + "\n",
                style="#9aa0a6",
            )
            text.append(
                t("now: ") + M.format_raw(self.store.get(key), 80), style="#9aa0a6"
            )
        else:
            lines = M.describe(
                row.field,
                self.store.get(key),
                row.field.make_default(),
                issues,
                changed=changed,
                ignored=ignored_by_override(key, self.store.get(OVERRIDE_KEY)),
                forced_off=key == akashi.ENABLED_KEY
                and akashi.forced_off(self.store.as_dict()),
            )
            for i, line in enumerate(lines):
                text.append(line.text, style=line.style or None)
                if i < len(lines) - 1:
                    text.append("\n")
        panel.update(text)

    def _on_store_change(self, key: Optional[str]) -> None:
        for row in self._field_rows():
            row.refresh()
        self.query_one(ModuleList).refresh()
        self._refresh_top()
        focused = self.focused
        if isinstance(focused, FieldRow):
            self._update_help(focused)

    # ------------------------------------------------------------------ #
    # editing
    # ------------------------------------------------------------------ #
    def _current_row(self) -> Optional[FieldRow]:
        return self.focused if isinstance(self.focused, FieldRow) else None

    def action_edit(self) -> None:
        """Enter: second level = confirm and return to the list; first level = enter this row (adjustable → edit, otherwise open a dialog)."""
        if self._edit_row is not None:
            self._end_edit(confirm=True)
            return
        row = self._current_row()
        if row is not None:
            self._open_editor(row)

    @on(FieldRow.Activated)
    def _row_activated(self, event: FieldRow.Activated) -> None:
        self._open_editor(event.row, click=True)

    @on(FieldRow.EnterEdit)
    def _row_enter_edit(self, event: FieldRow.EnterEdit) -> None:
        if self._edit_row is None:
            self._begin_edit(event.row)

    def action_quick(self) -> None:
        """Space: first level = same as Enter; second level = next value (wraps around at the end)."""
        if self._edit_row is not None:
            self._adjust_row(self._edit_row, 1, wrap=True)
            return
        self.action_edit()

    def action_adjust(self, delta: int) -> None:
        """+ / -: only effective while editing (integer ±1, enum cycle, switch)."""
        if self._edit_row is not None:
            self._adjust_row(self._edit_row, delta)

    # --- second-level editing: switch / enum / integer with few levels ------- #
    def _begin_edit(self, row: FieldRow) -> None:
        if row.field is None or not M.adjustable(row.field) or isinstance(row, BulkRow):
            return
        self._edit_row = row
        self._edit_before = self.store.get(row.key)
        row.in_edit = True
        row.set_class(True, "editing")
        row.refresh()
        self._refresh_hints()

    def _end_edit(self, *, confirm: bool) -> None:
        row = self._edit_row
        if row is None:
            return
        self._edit_row = None
        if not confirm:
            self.store.set(
                row.key, self._edit_before
            )  # Esc: restore the value from before entering
        row.in_edit = False
        row.set_class(False, "editing")
        row.refresh()
        self._refresh_hints()

    def _adjust_row(self, row: FieldRow, delta: int, *, wrap: bool = False) -> None:
        if row.field is None or isinstance(row, BulkRow):
            return
        if row.field.kind not in (Kind.INT, Kind.ENUM, Kind.BOOL):
            return
        value = self.store.get(row.key)
        self._commit(row.key, M.adjust_value(row.field, value, delta, wrap=wrap))

    @on(FieldRow.Adjust)
    def _row_adjust(self, event: FieldRow.Adjust) -> None:
        self._adjust_row(event.row, event.delta)

    def action_reset_default(self) -> None:
        row = self._current_row()
        if row is None or self._edit_row is not None:
            return
        if isinstance(row, BulkRow):
            for key in M.EXPEDITION_FLEET_KEYS:
                self.store.reset_key(key)
            return
        if row.field is None:
            self.app.notify(t("Unknown keys have no default"), timeout=2)
            return
        self.store.reset_key(row.key)

    def action_undo(self) -> None:
        row = self._current_row()
        if self._edit_row is not None:
            return
        if isinstance(row, BulkRow):
            for key in M.EXPEDITION_FLEET_KEYS:
                self.store.revert_key(key)
        elif row is not None:
            self.store.revert_key(row.key)

    def action_close(self) -> None:
        """Esc: second level = discard this edit and return to the list; first level = leave the editor."""
        if self._edit_row is not None:
            self._end_edit(confirm=False)
            return
        self.app.pop_screen()

    def action_search(self) -> None:
        if self._edit_row is not None:
            return
        self.app.push_screen(
            SearchDialog(M.unknown_keys(self.store.as_dict())), self._search_done
        )

    def _search_done(self, result: Optional[Picked]) -> None:
        if result is None:
            return
        key = result.value
        module = key.split(".", 1)[0] if key in SCHEMA else M.OTHER
        names = [e.module for e in M.MODULE_ENTRIES]
        if module not in names:
            return
        self._show_module(names.index(module))

        def focus_row() -> None:
            for row in self._field_rows():
                if row.key == key:
                    row.focus()
                    return

        self.call_after_refresh(focus_row)

    # ------------------------------------------------------------------ #
    def _noro6_nodes(self) -> M.NodeIndex:
        """Sortie presets in noro6 that specify a target node; decompression takes a moment, so it is only read once."""
        if self._noro6_cache is None:
            self._noro6_cache = noro6.load_sortie_nodes(self.project_root)
        return self._noro6_cache

    def _quest_catalog(self) -> list[M.QuestInfo]:
        if self._catalog is None:
            self._catalog = M.load_quest_catalog(self.project_root)
        return self._catalog

    def _open_editor(self, row: FieldRow, *, click: bool = False) -> None:
        if isinstance(row, BulkRow):
            self._open_bulk()
            return
        key, field = row.key, row.field
        value = self.store.get(key)
        kind = M.editor_for(field, value)
        push = self.app.push_screen
        done = partial(self._dialog_done, key)
        is_list = isinstance(value, list)

        if kind in ("bool", "choice") or (kind == "choice_int" and _is_int(value)):
            # switch / enum / integer with few levels: no dialog. Enter starts editing (second level),
            # ← → change the value, Enter confirms, Esc restores, then back to the list (first level)
            self._begin_edit(row)
        elif kind == "wheel" and _is_int(value):
            spec = NumSpec(field.label, value, field.min, field.max)
            push(NumberDialog(field, field.label, [spec], as_list=False), done)
        elif kind == "map":
            push(MapDialog(field, value, self._noro6_nodes()), done)
        elif (
            kind == "recipe"
            and is_list
            and len(value) == 4
            and all(_is_int(v) for v in value)
        ):
            # layout: top fuel / steel, bottom ammo / bauxite; the order is still the config file's [fuel, ammo, steel, bauxite]
            specs = [
                NumSpec(
                    name,
                    v,
                    field.min,
                    field.max,
                    min_places=3,
                    color=color,
                    row=row,
                    col=col,
                )
                for (name, color, row, col), v in zip(M.RESOURCES, value)
            ]
            dlg_kind = (
                "build"
                if key == "factory.build_recipe"
                else "develop"
                if key == "factory.develop_recipe"
                else ""
            )
            presets = (
                M.load_recipe_presets(self.project_root, dlg_kind) if dlg_kind else []
            )
            sec_key = f"factory.{dlg_kind}_secretary" if dlg_kind else ""
            dlg = NumberDialog(
                field,
                field.label,
                specs,
                as_list=True,
                presets=presets,
                secretary_key=sec_key,
            )
            push(dlg, partial(self._recipe_done, key, dlg))
        elif kind == "secretary" and not isinstance(value, (dict, list)):
            push(SecretaryDialog(field, value), done)
        elif kind == "text" and not isinstance(value, (dict, list)):
            push(TextDialog(field, value), done)
        elif kind == "preset_wheel" and (field.kind is Kind.PRESET or is_list):
            push(PresetWheelDialog(field, value), done)
        elif kind == "scheduler" and is_list:
            push(SchedulerDialog(field, value), done)
        elif kind == "table" and is_list:
            push(TableDialog(field, value), done)
        elif kind == "quest" and is_list and self._quest_catalog():
            push(QuestDialog(field, value, self._quest_catalog()), done)
        elif kind == "tokens" and is_list and not M.has_duplicates(value):
            push(
                PresetDialog(
                    field,
                    value,
                    multi=True,
                    tokens=("1", "2", "3"),
                    hint=t("Space toggles a group · Enter = OK"),
                ),
                done,
            )
        elif kind in ("list", "quest", "tokens", "table") and is_list:
            push(ListDialog(field, value), done)
        elif kind == "tree" and isinstance(value, dict):
            push(TreeDialog(field.label, field.help, value, field=field), done)
        elif field is None and isinstance(value, (dict, list)):
            push(
                TreeDialog(key, t("Unknown key — kept as-is when saving."), value), done
            )
        else:  # json / value with a corrupt type
            title = field.label if field else key
            help_text = field.help if field else t("Unknown key — edit as JSON.")
            want_object = bool(field and field.kind is Kind.OBJECT)
            push(JsonDialog(title, help_text, value, want_object=want_object), done)

    # --- expeditions: set fleets 2/3/4 at once ------------------------------ #
    def _open_bulk(self) -> None:
        current = M.expedition_common(self.store.as_dict())
        self.app.push_screen(
            ChoiceDialog(
                t("All fleets 2 / 3 / 4"),
                t("Set the expedition destinations of all three fleets at once."),
                M.expedition_bulk_options(),
                current,
            ),
            self._bulk_chosen,
        )

    def _bulk_chosen(self, result: Optional[Picked]) -> None:
        if result is None:
            return
        choice = result.value
        if choice == M.CUSTOM:
            first = self.store.get(M.EXPEDITION_FLEET_KEYS[0])
            same = all(self.store.get(k) == first for k in M.EXPEDITION_FLEET_KEYS)
            items = first if same and isinstance(first, list) else []
            field = SCHEMA[M.EXPEDITION_FLEET_KEYS[0]]
            self.app.push_screen(ListDialog(field, items), self._bulk_custom)
        elif choice == M.CLEAR:
            self._apply_bulk([])
        else:
            self._apply_bulk(M.expedition_preset_items(choice))

    def _bulk_custom(self, result: Optional[Picked]) -> None:
        if result is not None:
            self._apply_bulk(result.value)

    def _apply_bulk(self, items: list) -> None:
        for key in M.EXPEDITION_FLEET_KEYS:
            self.store.set(key, list(items))

    def _recipe_done(
        self, key: str, dlg: NumberDialog, result: Optional[Picked]
    ) -> None:
        if result is None:
            return
        self._commit(key, result.value)
        if dlg.has_sec and dlg.secretary_key:
            self._commit(dlg.secretary_key, dlg.sec_value)

    def _dialog_done(self, key: str, result: Optional[Picked]) -> None:
        if result is not None:
            self._commit(key, result.value)

    def _commit(self, key: str, value: Any) -> None:
        old = self.store.get(key)
        if value == old and type(value) is type(old):
            return
        field = SCHEMA.get(key)
        if field is not None and M.needs_danger_confirm(field, old, value):
            added = M.added_items(old, value)

            def confirmed(ok: Optional[bool]) -> None:
                if ok:
                    self.store.set(key, value)

            self.app.push_screen(DangerDialog(field, added), confirmed)
            return
        self.store.set(key, value)
