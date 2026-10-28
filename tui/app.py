"""kcauto_custom CUI 主程式(btop 風格儀表板)。

階段 3:kcauto 行程控制(套用並重啟、暫停、停止)、日誌、狀態列的行程資訊。
尚未實作:完整編輯器(階段 4)。

按鍵
    方向鍵        在方框間移動(日誌方框取得焦點時改為捲動日誌)
    c e p u s f r h v g   直接跳到該模組方框
    space         切換模組 enabled;焦點在日誌時改為暫停/繼續 kcauto
    enter         開啟編輯器;焦點在日誌且 kcauto 在等待時送出 Enter
    a             套用:存檔後(重新)啟動 kcauto
    b             暫停/繼續 kcauto(任何位置皆可)
    k             停止 kcauto
    l             聚焦日誌;日誌被隱藏時改為全螢幕檢視
    esc           離開日誌 / 全螢幕日誌
    w             存檔      q  離開
"""
from __future__ import annotations

import asyncio
from collections import deque
from pathlib import Path

from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Static

from .layout import (
    ALL_CLASSES, LOG_HIDDEN, LayoutPlan, card_heights, choose_layout,
)
from .modules import CARDS, CARD_BY_MODULE, CardSpec, hotkey_markup, move_index
from .runner import LOG_SYSTEM, RunState, Runner
from .store import ConfigStore, ConfigValidationError
from .widgets.bars import HintBar, StatusBar
from .widgets.box import Box
from .widgets.card import ModuleCard
from .widgets.logbox import LogBox

CPU_HISTORY = 60   # 狀態列迷你圖的取樣數(每秒一筆)


class ConfirmQuit(ModalScreen[str]):
    """離開確認。回傳 'save' / 'discard' / 'cancel'。

    dirty:有未儲存修改;running:kcauto 仍在執行(離開會一併終止它)。
    """

    BINDINGS = [
        Binding("s", "choose('save')", "Save"),
        Binding("d", "choose('discard')", "Discard"),
        Binding("escape", "choose('cancel')", "Cancel"),
    ]

    def __init__(self, *, dirty: bool, running: bool) -> None:
        super().__init__()
        self.dirty = dirty
        self.running = running

    def compose(self) -> ComposeResult:
        body = Text()
        if self.dirty:
            body.append("有尚未儲存的修改\n", style="bold #e5c07b")
        else:
            body.append("kcauto 仍在執行\n", style="bold #e5c07b")
        if self.running:
            body.append("離開時會一併終止 kcauto\n", style="#9aa0a6")
        body.append("\n")

        options = []
        if self.dirty:
            options.append(("s", "儲存並離開"))
            options.append(("d", "放棄修改並離開"))
        else:
            options.append(("d", "終止 kcauto 並離開"))
        options.append(("esc", "取消"))
        for key, desc in options:
            body.append(f" {key} ", style="bold #0f1115 on #e5c07b")
            body.append(f" {desc}\n")
        with Vertical(id="quit-dialog"):
            yield Static(body)

    def action_choose(self, choice: str) -> None:
        if choice == "save" and not self.dirty:
            return
        self.dismiss(choice)


class KcautoCui(App):
    CSS_PATH = "theme.tcss"
    TITLE = "kcauto_custom"
    ENABLE_COMMAND_PALETTE = False     # Ctrl+P 的命令面板用不到

    BINDINGS = [
        Binding("q", "request_quit", "Quit"),
        Binding("w", "save_config", "Save"),
        Binding("a", "apply_config", "Apply"),
        Binding("b", "toggle_pause", "Pause"),
        Binding("k", "stop_kcauto", "Stop"),
        Binding("l", "focus_log", "Log"),
        Binding("escape", "leave_log", "Back", show=False),
        Binding("space", "toggle_focused", "Toggle", show=False),
        Binding("enter", "edit_focused", "Edit", show=False),
        Binding("up", "move_focus(0,-1)", "Up", show=False),
        Binding("down", "move_focus(0,1)", "Down", show=False),
        Binding("left", "move_focus(-1,0)", "Left", show=False),
        Binding("right", "move_focus(1,0)", "Right", show=False),
        *(
            Binding(c.hotkey, f"focus_card('{c.module}')", c.label, show=False)
            for c in CARDS
        ),
    ]

    def __init__(self, store: ConfigStore, runner: Runner | None = None,
                 *, autostart: bool = False) -> None:
        super().__init__()
        self.store = store
        self.runner = runner or Runner(config_name=Path(store.path).stem)
        self.runner.on_log = self._on_runner_log
        self.runner.on_state = self._on_runner_state
        self.autostart = autostart
        self.layout_plan: LayoutPlan | None = None
        self._cpu_history: deque[float] = deque(maxlen=CPU_HISTORY)
        self._runner_lock = asyncio.Lock()
        self._last_card_id = CARDS[0].card_id

    # ------------------------------------------------------------------ #
    # 版面
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        yield StatusBar(id="status")
        with Horizontal(id="main"):
            with Grid(id="cards"):
                for spec in CARDS:
                    yield ModuleCard(spec)
            log_box = LogBox(id="log-box")
            log_box.border_title = hotkey_markup("log", "l")
            yield log_box
        yield HintBar(id="hints")

    def on_mount(self) -> None:
        self.store.subscribe(self._on_store_change)
        self._on_store_change(None)
        self._apply_layout(self.size.width, self.size.height)
        self.query_one(f"#{CARDS[0].card_id}", ModuleCard).focus()
        self.query_one(LogBox).add(
            LOG_SYSTEM, "kcauto 尚未啟動 — 按 a 存檔並啟動(已在執行時為重新啟動)")
        self.set_interval(1.0, self._tick)
        if self.autostart:
            self._spawn(self._do_restart())

    def on_unmount(self) -> None:
        self.store.unsubscribe(self._on_store_change)
        self.runner.kill_now()      # 不論如何離開,都不留下孤兒行程

    def on_resize(self, event: events.Resize) -> None:
        self._apply_layout(event.size.width, event.size.height)

    @on(events.DescendantFocus)
    def _remember_card(self, event: events.DescendantFocus) -> None:
        if isinstance(event.widget, ModuleCard):
            self._last_card_id = event.widget.id

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
        if plan.log != LOG_HIDDEN:
            main.remove_class("log-full")       # 日誌已經看得到,不需要全螢幕
        self._sync_log_later()

    def _sync_log_later(self) -> None:
        log = self._query_or_none(LogBox)
        if log is not None:
            self.call_after_refresh(log.sync)

    def _query_or_none(self, selector):
        try:
            return self.query_one(selector)
        except NoMatches:
            return None

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
    # runner → UI(callback 在 asyncio 任務中呼叫,與 UI 同一個事件迴圈)
    # ------------------------------------------------------------------ #
    def _on_runner_log(self, kind: str, text: str) -> None:
        log = self._query_or_none(LogBox)
        if log is not None:
            log.add(kind, text)

    def _on_runner_state(self, state: RunState, waiting: bool) -> None:
        bar = self._query_or_none(StatusBar)
        if bar is None:
            return
        bar.set_run(state.value, waiting)
        if state is RunState.STOPPED:
            self._cpu_history.clear()
        bar.refresh_from(self.store)
        if waiting:
            self.notify("kcauto 在等待 Enter:在日誌方框按 Enter 繼續",
                        severity="warning", timeout=10)
            self._reveal_log()

    def _tick(self) -> None:
        """每秒更新行程資訊(CPU、記憶體、執行時間)。"""
        bar = self._query_or_none(StatusBar)
        if bar is None:
            return
        sample = self.runner.sample()
        if sample is None:
            if bar.sample is not None:
                bar.set_process(None)
                bar.refresh_from(self.store)
            return
        self._cpu_history.append(sample.cpu)
        bar.set_process(sample, list(self._cpu_history))
        bar.refresh_from(self.store)

    # ------------------------------------------------------------------ #
    # 動作:方框導覽與編輯
    # ------------------------------------------------------------------ #
    def _modal_open(self) -> bool:
        return isinstance(self.screen, ModalScreen)

    def _focused_card(self) -> ModuleCard | None:
        focused = self.focused
        return focused if isinstance(focused, ModuleCard) else None

    def _focused_log(self) -> bool:
        return isinstance(self.focused, LogBox)

    def action_focus_card(self, module: str) -> None:
        if self._modal_open():
            return
        self.query_one(f"#card-{module}", ModuleCard).focus()

    def action_move_focus(self, dx: int, dy: int) -> None:
        if self._modal_open():
            return
        card = self._focused_card()
        if card is None:
            self.query_one(f"#{self._last_card_id}", ModuleCard).focus()
            return
        index = CARDS.index(card.spec)
        columns = self.layout_plan.columns if self.layout_plan else 2
        target = CARDS[move_index(index, dx, dy, columns=columns)]
        self.action_focus_card(target.module)

    def action_toggle_focused(self) -> None:
        if self._modal_open():
            return
        if self._focused_log():
            self.action_toggle_pause()
            return
        card = self._focused_card()
        if card is not None and card.spec.toggleable:
            self._toggle(card.spec)

    def action_edit_focused(self) -> None:
        if self._modal_open():
            return
        if self._focused_log():
            if self.runner.waiting_enter:
                self._spawn(self._send_enter())
            return
        card = self._focused_card()
        if card is not None:
            self._edit(card.spec)

    def action_save_config(self) -> None:
        if self._modal_open():
            return
        self._save()

    # ------------------------------------------------------------------ #
    # 動作:kcauto 行程
    # ------------------------------------------------------------------ #
    def action_apply_config(self) -> None:
        """存檔後(重新)啟動 kcauto。有錯誤時不啟動。"""
        if self._modal_open():
            return
        if self.store.has_errors():
            count = sum(1 for i in self.store.issues() if i.level == "error")
            self.notify(f"設定有 {count} 個錯誤,未啟動 kcauto", severity="error",
                        timeout=6)
            return
        if (self.store.changed_keys() or self.store.is_new_file) and not self._save():
            return
        self._spawn(self._do_restart())

    def action_stop_kcauto(self) -> None:
        if self._modal_open():
            return
        if self.runner.state is RunState.STOPPED:
            self.notify("kcauto 沒有在執行", timeout=2)
            return
        self._spawn(self._do_stop())

    def action_toggle_pause(self) -> None:
        if self._modal_open():
            return
        if self.runner.toggle_pause() is None:
            self.notify("kcauto 沒有在執行", timeout=2)

    def action_focus_log(self) -> None:
        if self._modal_open():
            return
        main = self.query_one("#main")
        if self.layout_plan is not None and self.layout_plan.log == LOG_HIDDEN:
            if main.has_class("log-full"):
                self._leave_log()
            else:
                self._reveal_log()
        else:
            self.query_one(LogBox).focus()

    def action_leave_log(self) -> None:
        if self._modal_open():
            return
        main = self.query_one("#main")
        if main.has_class("log-full") or self._focused_log():
            self._leave_log()

    def _reveal_log(self) -> None:
        """讓日誌可見並取得焦點(版面放不下時改成全螢幕日誌)。"""
        if self._modal_open():
            return
        main = self.query_one("#main")
        if self.layout_plan is not None and self.layout_plan.log == LOG_HIDDEN:
            main.add_class("log-full")
        log = self.query_one(LogBox)

        def focus_log() -> None:
            log.sync()
            log.focus()

        self.call_after_refresh(focus_log)

    def _leave_log(self) -> None:
        self.query_one("#main").remove_class("log-full")
        self.query_one(f"#{self._last_card_id}", ModuleCard).focus()
        self._sync_log_later()

    def _spawn(self, coroutine) -> None:
        self.run_worker(self._guarded(coroutine), group="runner", exclusive=False)

    async def _guarded(self, coroutine) -> None:
        """worker 內的未預期例外只記到日誌,不讓整個 UI 結束。"""
        try:
            await coroutine
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._on_runner_log(LOG_SYSTEM, f"內部錯誤:{exc!r}")

    async def _do_restart(self) -> None:
        async with self._runner_lock:
            await self.runner.restart()

    async def _do_stop(self) -> None:
        async with self._runner_lock:
            await self.runner.stop()

    async def _send_enter(self) -> None:
        await self.runner.send_enter()

    async def _shutdown(self) -> None:
        try:
            async with self._runner_lock:
                await self.runner.stop()
        finally:
            self.exit()          # 即使停止失敗也要離開;on_unmount 會再保險地 kill

    # ------------------------------------------------------------------ #
    # 離開
    # ------------------------------------------------------------------ #
    def action_request_quit(self) -> None:
        if self._modal_open():
            return
        dirty = bool(self.store.changed_keys())
        running = self.runner.state is not RunState.STOPPED
        if not dirty and not running:
            self.exit()
            return
        self.push_screen(ConfirmQuit(dirty=dirty, running=running),
                         self._on_quit_choice)

    def _on_quit_choice(self, choice: str | None) -> None:
        if choice == "save":
            if self._save():
                self._spawn(self._shutdown())
        elif choice == "discard":
            self._spawn(self._shutdown())

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
