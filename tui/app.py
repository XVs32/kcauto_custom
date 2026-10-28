"""kcauto_custom CUI 主程式(btop 風格儀表板)。

階段 2:儀表板、聚焦/導覽、模組開關、存檔、離開確認。
尚未實作:完整編輯器(階段 4)、kcauto 行程控制與日誌(階段 3)。
"""
from __future__ import annotations

from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from .layout import ALL_CLASSES, LayoutPlan, card_heights, choose_layout
from .modules import CARDS, CARD_BY_MODULE, CardSpec, hotkey_markup, move_index
from .store import ConfigStore, ConfigValidationError
from .widgets.bars import HintBar, StatusBar
from .widgets.box import Box
from .widgets.card import ModuleCard


class ConfirmQuit(ModalScreen[str]):
    """有未儲存修改時的離開確認。回傳 'save' / 'discard' / 'cancel'。"""

    BINDINGS = [
        Binding("s", "choose('save')", "Save"),
        Binding("d", "choose('discard')", "Discard"),
        Binding("escape", "choose('cancel')", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        body = Text()
        body.append("有尚未儲存的修改\n\n", style="bold #e5c07b")
        for key, desc in (("s", "儲存並離開"), ("d", "放棄修改並離開"),
                          ("esc", "取消")):
            body.append(f" {key} ", style="bold #0f1115 on #e5c07b")
            body.append(f" {desc}\n")
        with Vertical(id="quit-dialog"):
            yield Static(body)

    def action_choose(self, choice: str) -> None:
        self.dismiss(choice)


class KcautoCui(App):
    CSS_PATH = "theme.tcss"
    TITLE = "kcauto_custom"

    BINDINGS = [
        Binding("q", "request_quit", "Quit"),
        Binding("w", "save", "Save"),
        Binding("space", "toggle_focused", "Toggle", show=False),
        Binding("enter", "edit_focused", "Edit", show=False),
        Binding("up", "move(0,-1)", "Up", show=False),
        Binding("down", "move(0,1)", "Down", show=False),
        Binding("left", "move(-1,0)", "Left", show=False),
        Binding("right", "move(1,0)", "Right", show=False),
        *(
            Binding(c.hotkey, f"focus_card('{c.module}')", c.label, show=False)
            for c in CARDS
        ),
    ]

    def __init__(self, store: ConfigStore) -> None:
        super().__init__()
        self.store = store
        self.layout_plan: LayoutPlan | None = None   # 目前套用的版面規劃

    # ------------------------------------------------------------------ #
    # 版面
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        yield StatusBar(id="status")
        with Horizontal(id="main"):
            with Grid(id="cards"):
                for spec in CARDS:
                    yield ModuleCard(spec)
            log_box = Static(
                Text("kcauto 尚未連接(階段 3 提供啟動、暫停與日誌)", style="#6b7280"),
                id="log-box",
            )
            log_box.border_title = hotkey_markup("log", "l")
            yield log_box
        yield HintBar(id="hints")

    def on_mount(self) -> None:
        self.store.subscribe(self._on_store_change)
        self._on_store_change(None)
        self._apply_layout(self.size.width, self.size.height)
        self.query_one(f"#{CARDS[0].card_id}", ModuleCard).focus()

    def on_unmount(self) -> None:
        self.store.unsubscribe(self._on_store_change)

    def on_resize(self, event: events.Resize) -> None:
        self._apply_layout(event.size.width, event.size.height)

    def _apply_layout(self, width: int, height: int) -> None:
        """依終端機大小(與方框內容高度)決定欄數與日誌位置。

        版面 class 設在 #main 上而不是 Screen,這樣對話框開著時縮放視窗也不會錯位。
        """
        plan = choose_layout(width, height, card_heights(self.store.as_dict()))
        if plan == self.layout_plan:
            return
        self.layout_plan = plan
        main = self.query_one("#main")
        for name in ALL_CLASSES:
            main.set_class(name in plan.classes, name)

    # ------------------------------------------------------------------ #
    # store → UI
    # ------------------------------------------------------------------ #
    def _on_store_change(self, key: str | None) -> None:
        values = self.store.as_dict()
        if key is None:
            for card in self.query(ModuleCard):
                card.show(values)
        else:
            spec = CARD_BY_MODULE.get(key.split(".", 1)[0])
            if spec is not None:
                self.query_one(f"#{spec.card_id}", ModuleCard).show(values)
        self.query_one(StatusBar).refresh_from(self.store)
        # 方框內容的行數會影響「日誌放下方是否放得下」,內容變動時重新評估
        if self.layout_plan is not None:
            self._apply_layout(self.size.width, self.size.height)

    # ------------------------------------------------------------------ #
    # 動作
    # ------------------------------------------------------------------ #
    def _modal_open(self) -> bool:
        return isinstance(self.screen, ModalScreen)

    def _focused_card(self) -> ModuleCard | None:
        focused = self.focused
        return focused if isinstance(focused, ModuleCard) else None

    def action_focus_card(self, module: str) -> None:
        if self._modal_open():
            return
        self.query_one(f"#card-{module}", ModuleCard).focus()

    def action_move(self, dx: int, dy: int) -> None:
        if self._modal_open():
            return
        card = self._focused_card()
        if card is None:
            self.action_focus_card(CARDS[0].module)
            return
        index = CARDS.index(card.spec)
        columns = self.layout_plan.columns if self.layout_plan else 2
        target = CARDS[move_index(index, dx, dy, columns=columns)]
        self.action_focus_card(target.module)

    def action_toggle_focused(self) -> None:
        if self._modal_open():
            return
        card = self._focused_card()
        if card is not None and card.spec.toggleable:
            self._toggle(card.spec)

    def action_edit_focused(self) -> None:
        if self._modal_open():
            return
        card = self._focused_card()
        if card is not None:
            self._edit(card.spec)

    def action_save(self) -> None:
        if self._modal_open():
            return
        self._save()

    def action_request_quit(self) -> None:
        if self._modal_open():
            return
        if not self.store.changed_keys():
            self.exit()
            return
        self.push_screen(ConfirmQuit(), self._on_quit_choice)

    # ------------------------------------------------------------------ #
    # 實作
    # ------------------------------------------------------------------ #
    def _toggle(self, spec: CardSpec) -> None:
        current = self.store.get(spec.enabled_key)
        self.store.set(spec.enabled_key, (not current) if isinstance(current, bool) else True)

    def _edit(self, spec: CardSpec) -> None:
        self.notify(f"「{spec.label}」的完整編輯器將在階段 4 提供", timeout=3)

    def _save(self) -> bool:
        try:
            path = self.store.save()
        except ConfigValidationError as exc:
            first = exc.issues[0].message
            self.notify(f"有 {len(exc.issues)} 個錯誤,未儲存:{first}",
                        severity="error", timeout=6)
            return False
        except OSError as exc:
            self.notify(f"寫入失敗:{exc}", severity="error", timeout=6)
            return False
        self.notify(f"已儲存 {path.name}", timeout=2)
        return True

    def _on_quit_choice(self, choice: str | None) -> None:
        if choice == "save":
            if self._save():
                self.exit()
        elif choice == "discard":
            self.exit()

    # ------------------------------------------------------------------ #
    # 滑鼠事件(由 Box 送出)
    # ------------------------------------------------------------------ #
    @on(Box.Toggled)
    def _box_toggled(self, event: Box.Toggled) -> None:
        if isinstance(event.box, ModuleCard) and not self._modal_open():
            self._toggle(event.box.spec)

    @on(Box.Activated)
    def _box_activated(self, event: Box.Activated) -> None:
        if isinstance(event.box, ModuleCard) and not self._modal_open():
            self._edit(event.box.spec)
