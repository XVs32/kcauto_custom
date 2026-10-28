"""全螢幕編輯器(btop Options 風格)。

   ┌ modules ┐┌ combat ─────────────────────────────┐
   │ ● combat ││ ── Basic ──                         │
   │ ○ exped… ││ * 啟用出擊               on         │
   │ …        ││   出擊海域               1-1        │
   └─────────┘└─────────────────────────────────────┘
   ┌ combat.sortie_map ─ help / type / default / issues ┐

所有修改都即時寫進 ConfigStore(儀表板同步更新);是否存檔由 w 決定。
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

from ..modules import CARD_BY_MODULE
from ..schema import SCHEMA, Field, Kind, fields_of, groups_of
from ..store import ConfigStore
from . import model as M
from .dialogs import (
    ChoiceDialog, DangerDialog, JsonDialog, ListDialog, Picked, PresetDialog,
    QuestDialog, RecipeDialog, SearchDialog, TableDialog, TextDialog,
)

FLAG_MARK = {"error": ("✖", "bold #e06c75"), "danger": ("!", "bold #c678dd"),
             "warning": ("⚠", "#e5c07b"), "": (" ", "")}
NARROW_WIDTH = 72

HINTS = (
    ("↑↓", "move"), ("enter", "edit"), ("space", "toggle"), ("+/-", "adjust"),
    ("d", "default"), ("z", "undo"), ("/", "search"), ("[ ]", "module"),
    ("w", "save"), ("esc", "back"),
)


# ---------------------------------------------------------------------- #
class ModuleList(Widget, can_focus=True):
    """左側的模組清單。↑↓ 換模組;Enter / → 進入右側表單。"""

    BINDINGS = [
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("enter,right", "enter_form", show=False),
    ]

    class Selected(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    class EnterForm(Message):
        pass

    def __init__(self, store: ConfigStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self.store = store
        self.index = 0
        self.styles.height = len(M.MODULE_ENTRIES)

    def action_move(self, delta: int) -> None:
        new = min(max(self.index + delta, 0), len(M.MODULE_ENTRIES) - 1)
        if new != self.index:
            self.post_message(self.Selected(new))

    def action_enter_form(self) -> None:
        self.post_message(self.EnterForm())

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.focus()
        if 0 <= event.y < len(M.MODULE_ENTRIES):
            self.post_message(self.Selected(event.y))
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
        for i, entry in enumerate(M.MODULE_ENTRIES):
            keys = set(M.module_keys(entry.module, values))
            n_changed = sum(1 for k in changed if k in keys)
            has_error = any(x.level == "error" and keys & set(x.keys) for x in issues)

            selected = i == self.index
            bg = ("on #3a4150" if self.has_focus else "on #242932") if selected else ""
            line = Text(no_wrap=True)
            line.append("▌" if selected else " ", style=entry.color)
            spec = CARD_BY_MODULE.get(entry.module)
            if spec is not None and spec.toggleable:
                on_ = values.get(spec.enabled_key) is True
                line.append("● " if on_ else "○ ", style="#98c379" if on_ else "#6b7280")
            else:
                line.append("  ")
            before, hot, after = _split_hotkey(entry.label, entry.hotkey)
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


def _split_hotkey(label: str, hotkey: str) -> tuple[str, str, str]:
    index = label.lower().find(hotkey.lower())
    if index < 0:
        return label, "", ""
    return label[:index], label[index], label[index + 1:]


# ---------------------------------------------------------------------- #
class FieldRow(Widget, can_focus=True):
    """表單中的一列:旗標、修改標記、標籤、值。單擊即編輯。"""

    class Activated(Message):
        def __init__(self, row: "FieldRow") -> None:
            super().__init__()
            self.row = row

    def __init__(self, store: ConfigStore, key: str) -> None:
        super().__init__()
        self.store = store
        self.key = key
        self.field: Optional[Field] = SCHEMA.get(key)

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.focus()
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

        label_w = max(12, min(30, width * 2 // 5))
        value_w = max(4, width - label_w - 5)
        label = field.label if field else self.key
        dim = bool(field and field.advanced)

        mark, mark_style = FLAG_MARK[flag]
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(mark, style=mark_style)
        text.append("*" if changed else " ", style="bold #e5c07b")
        text.append(" ")
        text.append(M.pad_cells(label, label_w), style="#6b7280" if dim else "")
        text.append("  ")
        shown = M.format_value(field, value, value_w) if field else M.format_raw(value, value_w)
        text.append(shown, style=_value_style(value, flag, changed))
        return text


def _value_style(value: Any, flag: str, changed: bool) -> str:
    if flag == "error":
        return "#e06c75"
    if value is True:
        return "#98c379"
    if value is False or value is None:
        return "#7f848e"
    return "#e5c07b" if changed else "#c8ccd4"


class FormPane(VerticalScroll, can_focus=False):
    """一個模組的表單(依 group 分區)。所有模組的 pane 同時存在,只顯示被選的那個。"""

    def __init__(self, store: ConfigStore, module: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.store = store
        self.module = module

    def compose(self) -> ComposeResult:
        if self.module == M.OTHER:
            keys = M.unknown_keys(self.store.as_dict())
            if not keys:
                yield Static(Text("No unknown keys. Settings kcauto adds in newer "
                                  "versions show up here and are kept when saving.",
                                  style="#6b7280"), classes="grp")
            for key in keys:
                yield FieldRow(self.store, key)
            return
        for group in groups_of(self.module):
            yield Static(Text(f"── {M.group_title(group)} ──", style="bold #7f848e"),
                         classes="grp")
            for field in fields_of(self.module):
                if field.group == group:
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
        Binding("left_square_bracket,[", "module(-1)", show=False),
        Binding("right_square_bracket,]", "module(1)", show=False),
        Binding("enter", "edit", show=False),
        Binding("space", "quick", show=False),
        Binding("plus,+,equals_sign,=", "adjust(1)", show=False),
        Binding("minus,-", "adjust(-1)", show=False),
        Binding("d", "reset_default", show=False),
        Binding("z", "undo", show=False),
        Binding("slash,/", "search", show=False),
        Binding("w", "save", show=False),
        *(Binding(e.hotkey, f"goto_module('{e.module}')", show=False)
          for e in M.MODULE_ENTRIES),
    ]

    def __init__(self, store: ConfigStore, module: str, *,
                 save: Callable[[], bool] | None = None,
                 data_dir: str = "data") -> None:
        super().__init__()
        self.store = store
        self.save_callback = save
        self.data_dir = data_dir
        self._catalog: Optional[list[str]] = None
        names = [e.module for e in M.MODULE_ENTRIES]
        self.index = names.index(module) if module in names else 0

    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        yield Static(id="ed-top")
        with Horizontal(id="ed-body"):
            with Vertical(id="ed-left"):
                yield ModuleList(self.store, id="ed-modules")
            with Vertical(id="ed-right"):
                for entry in M.MODULE_ENTRIES:
                    pane = FormPane(self.store, entry.module, id=f"pane-{entry.module}")
                    pane.display = False
                    yield pane
        yield Static(id="ed-help")
        yield Static(self._hints(), id="ed-hints")

    @staticmethod
    def _hints() -> Text:
        text = Text(no_wrap=True, overflow="ellipsis")
        for key, desc in HINTS:
            text.append(key, style="bold #e5c07b")
            text.append(f" {desc}  ", style="#9aa0a6")
        return text

    def on_mount(self) -> None:
        self.query_one("#ed-left").border_title = "modules"
        self.store.subscribe(self._on_store_change)
        self.set_class(self.size.width < NARROW_WIDTH, "narrow")
        self._show_module(self.index)
        self.call_after_refresh(self._focus_first_row)

    def on_unmount(self) -> None:
        self.store.unsubscribe(self._on_store_change)

    def on_resize(self, event: events.Resize) -> None:
        self.set_class(event.size.width < NARROW_WIDTH, "narrow")

    # ------------------------------------------------------------------ #
    # 模組切換
    # ------------------------------------------------------------------ #
    @property
    def entry(self) -> M.ModuleEntry:
        return M.MODULE_ENTRIES[self.index]

    def _pane(self, module: str) -> FormPane:
        return self.query_one(f"#pane-{module}", FormPane)

    def _rows(self) -> list[FieldRow]:
        return list(self._pane(self.entry.module).query(FieldRow))

    def _show_module(self, index: int) -> None:
        self.index = index
        for e in M.MODULE_ENTRIES:
            self._pane(e.module).display = (e.module == self.entry.module)
        right = self.query_one("#ed-right")
        right.border_title = self.entry.label
        right.styles.border = ("round", self.entry.color)
        right.styles.border_title_color = self.entry.color
        modules = self.query_one(ModuleList)
        modules.index = index
        modules.refresh()
        self._refresh_top()
        rows = self._rows()
        self._update_help(rows[0] if rows else None)

    def _focus_first_row(self) -> None:
        rows = self._rows()
        if rows:
            rows[0].focus()
            self._pane(self.entry.module).scroll_home(animate=False)

    @on(ModuleList.Selected)
    def _module_selected(self, event: ModuleList.Selected) -> None:
        self._show_module(event.index)

    @on(ModuleList.EnterForm)
    def _module_enter(self) -> None:
        self._focus_first_row()

    def action_goto_module(self, module: str) -> None:
        names = [e.module for e in M.MODULE_ENTRIES]
        self._show_module(names.index(module))
        self._focus_first_row()

    def action_module(self, delta: int) -> None:
        new = (self.index + delta) % len(M.MODULE_ENTRIES)
        self._show_module(new)
        if isinstance(self.focused, FieldRow):
            self._focus_first_row()

    def action_horizontal(self, direction: int) -> None:
        if self.has_class("narrow"):
            self.action_module(direction)
        elif direction < 0:
            self.query_one(ModuleList).focus()

    # ------------------------------------------------------------------ #
    # 列移動
    # ------------------------------------------------------------------ #
    def action_row(self, delta: int) -> None:
        rows = self._rows()
        if not rows:
            return
        focused = self.focused
        current = rows.index(focused) if focused in rows else (-1 if delta > 0 else len(rows))
        target = min(max(current + delta, 0), len(rows) - 1)
        rows[target].focus()
        if target == 0:
            self._pane(self.entry.module).scroll_home(animate=False)

    @on(events.DescendantFocus)
    def _focus_changed(self, event: events.DescendantFocus) -> None:
        if isinstance(event.widget, FieldRow):
            self._update_help(event.widget)

    # ------------------------------------------------------------------ #
    # 上下方資訊列
    # ------------------------------------------------------------------ #
    def _refresh_top(self) -> None:
        issues = self.store.issues()
        errors = sum(1 for i in issues if i.level == "error")
        warnings = sum(1 for i in issues if i.level != "error")
        n = len(self.store.changed_keys())
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(" Editor ", style="bold #0f1115 on #e5c07b")
        text.append(f"  {self.store.path.name}", style="bold")
        if n:
            text.append(f"  {n} modified*", style="bold #e5c07b")
        else:
            text.append("  saved", style="#6b7280")
        if errors:
            text.append(f"  ✖ {errors}", style="bold #e06c75")
        if warnings:
            text.append(f"  ⚠ {warnings}", style="#e5c07b")
        self.query_one("#ed-top", Static).update(text)

    def _update_help(self, row: Optional[FieldRow]) -> None:
        panel = self.query_one("#ed-help", Static)
        if row is None:
            panel.update(Text("(nothing here)", style="#6b7280"))
            return
        key = row.key
        issues = self.store.issues_for(key)
        changed = self.store.is_changed(key)
        text = Text()
        if row.field is None:
            text.append(key + "\n", style="bold")
            text.append("Unknown key — kept as-is when saving. Enter edits it as JSON.\n",
                        style="#9aa0a6")
            text.append("now: " + M.format_raw(self.store.get(key), 80), style="#9aa0a6")
        else:
            lines = M.describe(row.field, self.store.get(key), row.field.make_default(),
                               issues, changed=changed)
            for i, line in enumerate(lines):
                text.append(line.text, style=line.style or None)
                if i < len(lines) - 1:
                    text.append("\n")
        panel.update(text)

    def _on_store_change(self, key: Optional[str]) -> None:
        for row in self._rows():
            row.refresh()
        self.query_one(ModuleList).refresh()
        self._refresh_top()
        focused = self.focused
        if isinstance(focused, FieldRow):
            self._update_help(focused)

    # ------------------------------------------------------------------ #
    # 編輯
    # ------------------------------------------------------------------ #
    def _current_row(self) -> Optional[FieldRow]:
        return self.focused if isinstance(self.focused, FieldRow) else None

    def action_edit(self) -> None:
        row = self._current_row()
        if row is not None:
            self._open_editor(row)

    @on(FieldRow.Activated)
    def _row_activated(self, event: FieldRow.Activated) -> None:
        self._open_editor(event.row, click=True)

    def action_quick(self) -> None:
        """空白鍵:布林切換、enum 循環;其他型別等同 Enter。"""
        row = self._current_row()
        if row is None:
            return
        field, value = row.field, self.store.get(row.key)
        kind = M.editor_for(field, value)
        if kind == "bool":
            self._commit(row.key, not value if isinstance(value, bool) else True)
        elif kind == "choice" and field is not None:
            options = [v for _, v in M.enum_options(field)]
            self._commit(row.key, M.cycle_choice(options, value))
        else:
            self._open_editor(row)

    def action_adjust(self, delta: int) -> None:
        row = self._current_row()
        if row is None or row.field is None:
            return
        value = self.store.get(row.key)
        if row.field.kind is Kind.INT:
            new = M.step_int(row.field, value, delta)
            if new is not None:
                self._commit(row.key, new)
        elif row.field.kind is Kind.ENUM:
            options = [v for _, v in M.enum_options(row.field)]
            self._commit(row.key, M.cycle_choice(options, value, delta))
        elif row.field.kind is Kind.BOOL:
            self._commit(row.key, delta > 0)

    def action_reset_default(self) -> None:
        row = self._current_row()
        if row is None:
            return
        if row.field is None:
            self.app.notify("Unknown keys have no default", timeout=2)
            return
        self.store.reset_key(row.key)

    def action_undo(self) -> None:
        row = self._current_row()
        if row is not None:
            self.store.revert_key(row.key)

    def action_save(self) -> None:
        if self.save_callback is not None:
            self.save_callback()
        self._refresh_top()

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_search(self) -> None:
        self.app.push_screen(SearchDialog(M.unknown_keys(self.store.as_dict())),
                             self._search_done)

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
            for row in self._rows():
                if row.key == key:
                    row.focus()
                    return

        self.call_after_refresh(focus_row)

    # ------------------------------------------------------------------ #
    def _quest_catalog(self) -> list[str]:
        if self._catalog is None:
            self._catalog = M.load_quest_catalog(self.data_dir)
        return self._catalog

    def _open_editor(self, row: FieldRow, *, click: bool = False) -> None:
        key, field = row.key, row.field
        value = self.store.get(key)
        kind = M.editor_for(field, value)
        push = self.app.push_screen
        done = partial(self._dialog_done, key)

        if kind == "bool":
            self._commit(key, not value if isinstance(value, bool) else True)
        elif kind == "choice":
            push(ChoiceDialog(field.label, field.help, M.enum_options(field), value), done)
        elif kind == "text":
            push(TextDialog(field, value), done)
        elif kind == "preset":
            push(PresetDialog(field, value, multi=False), done)
        elif kind == "recipe":
            push(RecipeDialog(field, value), done)
        elif kind == "table" and isinstance(value, list):
            push(TableDialog(field, value), done)
        elif kind == "quest" and isinstance(value, list) and self._quest_catalog():
            push(QuestDialog(field, value, self._quest_catalog()), done)
        elif kind == "preset_list" and isinstance(value, list) and not M.has_duplicates(value):
            push(PresetDialog(field, value, multi=True), done)
        elif kind in ("list", "quest", "preset_list", "table") and isinstance(value, list):
            push(ListDialog(field, value), done)
        else:                                       # json / 型別已損壞的值
            title = field.label if field else key
            help_text = field.help if field else "Unknown key — edit as JSON."
            want_object = bool(field and field.kind is Kind.OBJECT)
            push(JsonDialog(title, help_text, value, want_object=want_object), done)

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
