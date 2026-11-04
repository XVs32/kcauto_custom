"""kcauto_custom CUI main program (btop-style dashboard).

Stage 3: kcauto process control (apply and restart, pause, stop), log, process info in the status bar.
Stage 4: full-screen editor (open with Enter or a click on the focused box, see editor/screen.py).

Keys
    arrows        move between boxes (scroll the log while the log box has focus)
    c e p u s f r h v g   jump straight to that module's box
    space         pause / resume kcauto (works anywhere)
    \\            toggle enabled on the focused box
    enter         open the editor; on the log (or a click on a focused log): forward Enter if kcauto is
                  waiting, otherwise apply = confirm, save the config, then (re)start kcauto
    l             focus the log (not shown in the hint bar); when the log is hidden, show it full screen
    d             toggle debug output     t  language
    esc           leave the log / full-screen log
    q             quit (offers: save and quit / discard / cancel)
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

from . import i18n, keymap, prefs
from .editor.dialogs import ChoiceDialog
from .editor.screen import EditorScreen
from .layout import (
    ALL_CLASSES,
    LOG_BOTTOM,
    LOG_HIDDEN,
    LOG_RIGHT,
    LayoutPlan,
    card_heights,
    choose_layout,
)
from .summaries import apply_confirm_lines
from .modules import CARDS, CARD_BY_MODULE, CardSpec, hotkey_markup, move_index
from .runner import LOG_SYSTEM, RunState, Runner
from .store import ConfigStore, ConfigValidationError
from .widgets.bars import HintBar, StatusBar
from .widgets.box import Box
from .widgets.card import ModuleCard
from .widgets.logbox import LogBox

CPU_HISTORY = 60  # number of samples in the status bar sparkline (one per second)


class ConfirmQuit(ModalScreen[str]):
    """Quit confirmation. Returns 'save' / 'discard' / 'cancel'.

    "Save and quit" is the only way to save without applying (applying also restarts kcauto).
    dirty: there are unsaved changes; running: kcauto is still running (quitting stops it too).
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
            body.append("You have unsaved changes\n", style="bold #e5c07b")
        else:
            body.append("kcauto is still running\n", style="bold #e5c07b")
        if self.running:
            body.append("Quitting will also stop kcauto\n", style="#9aa0a6")
        body.append("\n")

        options = []
        if self.dirty:
            options.append(("s", "Save and quit"))
            options.append(("d", "Discard changes and quit"))
        else:
            options.append(("d", "Stop kcauto and quit"))
        options.append(("esc", "Cancel"))
        for key, desc in options:
            body.append(f" {key} ", style="bold #0f1115 on #e5c07b")
            body.append(f" {desc}\n")
        with Vertical(id="quit-dialog"):
            yield Static(body)

    def action_choose(self, choice: str) -> None:
        if choice == "save" and not self.dirty:
            return
        self.dismiss(choice)


class ClickLabel(Static):
    """A line of a confirmation dialog that can be clicked (the keys work as well)."""

    def __init__(self, content: Text, choice: str) -> None:
        super().__init__(content)
        self.choice = choice

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.screen.action_choose(self.choice)


class ConfirmApply(ModalScreen[bool]):
    """Asked before the config is saved and kcauto is (re)started. Returns True to go ahead."""

    BINDINGS = [
        Binding("y,enter", "choose('yes')", "Apply"),
        Binding("n,escape", "choose('no')", "Cancel"),
    ]

    def __init__(
        self, *, changes: int, running: bool, new_file: bool, file_name: str
    ) -> None:
        super().__init__()
        self.lines = apply_confirm_lines(changes, running, new_file, file_name)

    def compose(self) -> ComposeResult:
        with Vertical(id="apply-dialog"):
            title = Text("Apply the config?\n", style="bold #e5c07b")
            yield Static(title)
            yield Static(Text("\n".join(self.lines) + "\n", style="#9aa0a6"))
            for key, desc, choice in (
                ("y/enter", "Apply", "yes"),
                ("n/esc", "Cancel", "no"),
            ):
                line = Text()
                line.append(f" {key} ", style="bold #0f1115 on #e5c07b")
                line.append(f" {desc}")
                yield ClickLabel(line, choice)

    def action_choose(self, choice: str) -> None:
        self.dismiss(choice == "yes")


_KEYS = keymap.active()  # loaded once at start-up (see keymap.py)


class KcautoCui(App):
    CSS_PATH = "theme.tcss"
    TITLE = "kcauto_custom"
    ENABLE_COMMAND_PALETTE = False  # the Ctrl+P command palette is not needed

    # The command keys come from the keymap (loaded once at start-up, see keymap.py); the
    # navigation keys (arrows, Enter, Esc) are fixed.
    BINDINGS = [
        Binding(_KEYS.binding_key("quit"), "request_quit", "Quit"),
        Binding(_KEYS.binding_key("pause"), "toggle_pause", "Pause"),
        Binding(_KEYS.binding_key("log"), "focus_log", "Log"),
        Binding(
            _KEYS.binding_key("language"), "choose_language", "Language", show=False
        ),
        Binding("escape", "leave_log", "Back", show=False),
        Binding(_KEYS.binding_key("toggle"), "toggle_focused", "Toggle", show=False),
        Binding(_KEYS.binding_key("debug"), "toggle_debug", "Debug", show=False),
        Binding("enter", "edit_focused", "Edit", show=False),
        Binding("up", "move_focus(0,-1)", "Up", show=False),
        Binding("down", "move_focus(0,1)", "Down", show=False),
        Binding("left", "move_focus(-1,0)", "Left", show=False),
        Binding("right", "move_focus(1,0)", "Right", show=False),
        *(
            Binding(
                _KEYS.binding_key(f"module.{c.module}"),
                f"focus_card('{c.module}')",
                c.label,
                show=False,
            )
            for c in CARDS
        ),
    ]

    def __init__(
        self,
        store: ConfigStore,
        runner: Runner | None = None,
        *,
        autostart: bool = False,
    ) -> None:
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
    # layout
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        yield StatusBar(id="status")
        with Horizontal(id="main"):
            with Grid(id="cards"):
                for spec in CARDS:
                    yield ModuleCard(spec)
            log_box = LogBox(id="log-box")
            log_box.border_title = hotkey_markup("log", _KEYS.key("log"))
            yield log_box
        yield HintBar(id="hints")

    def on_mount(self) -> None:
        self.store.subscribe(self._on_store_change)
        self._on_store_change(None)
        self._apply_layout(self.size.width, self.size.height)
        self._dash.query_one(f"#{CARDS[0].card_id}", ModuleCard).focus()
        status = self._dash.query_one(StatusBar)
        status.debug = bool(getattr(self.runner, "debug", False))
        status.refresh_from(self.store)
        log = self._dash.query_one(LogBox)
        log.add(
            LOG_SYSTEM,
            "kcauto is not running — focus the log and press Enter (or click it) to "
            "save and start (restarts if already running)",
        )
        for problem in _KEYS.problems:  # mistakes in the custom key settings
            log.add(LOG_SYSTEM, f"Key settings: {problem}")
        if _KEYS.problems:
            self.notify(
                f"{len(_KEYS.problems)} problem(s) in the key settings; see the log",
                severity="warning",
                timeout=6,
            )
        self.set_interval(1.0, self._tick)
        if self.autostart:
            self._spawn(self._do_restart())

    def on_unmount(self) -> None:
        self.store.unsubscribe(self._on_store_change)
        self.runner.kill_now()  # never leave an orphan process behind, however we exit

    def on_resize(self, event: events.Resize) -> None:
        self._apply_layout(event.size.width, event.size.height)

    @on(events.DescendantFocus)
    def _remember_card(self, event: events.DescendantFocus) -> None:
        if isinstance(event.widget, ModuleCard):
            self._last_card_id = event.widget.id

    def _apply_layout(self, width: int, height: int) -> None:
        """Choose the column count and log position from the terminal size (and card content height).

        The layout classes live on #main rather than on the Screen, so resizing the window while a dialog is open does not misplace anything.
        """
        plan = choose_layout(width, height, card_heights(self.store.as_dict()))
        if plan == self.layout_plan:
            return
        self.layout_plan = plan
        main = self._dash.query_one("#main")
        for name in ALL_CLASSES:
            main.set_class(name in plan.classes, name)
        if plan.log != LOG_HIDDEN:
            main.remove_class(
                "log-full"
            )  # the log is already visible; no need for full screen
        self._sync_log_later()

    def _sync_log_later(self) -> None:
        log = self._query_or_none(LogBox)
        if log is not None:
            self.call_after_refresh(log.sync)

    def _query_or_none(self, selector):
        try:
            return self._dash.query_one(selector)
        except NoMatches:
            return None

    # ------------------------------------------------------------------ #
    # store → UI
    # ------------------------------------------------------------------ #
    def _on_store_change(self, key: str | None) -> None:
        for note in self.store.pop_forced():
            if note == "akashi":
                self.notify(
                    i18n.t("Akashi repair is off while combat is enabled"),
                    severity="warning",
                    timeout=4,
                )
            elif note == "combat_off":
                self.notify(
                    i18n.t(
                        "Combat is off: Akashi repair and passive repair were turned on"
                    ),
                    timeout=4,
                )
        values = self.store.as_dict()
        if key is None:
            for card in self._dash.query(ModuleCard):
                card.show(values)
        else:
            spec = CARD_BY_MODULE.get(key.split(".", 1)[0])
            if spec is not None:
                self._dash.query_one(f"#{spec.card_id}", ModuleCard).show(values)
        self._dash.query_one(StatusBar).refresh_from(self.store)
        # card content height affects whether the log fits below, so re-evaluate when content changes
        if self.layout_plan is not None:
            self._apply_layout(self.size.width, self.size.height)

    # ------------------------------------------------------------------ #
    # runner → UI (callbacks run in an asyncio task, on the same event loop as the UI)
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
            self.notify(
                "kcauto is waiting for Enter: press Enter in the log box to continue",
                severity="warning",
                timeout=10,
            )
            self._reveal_log()

    def _tick(self) -> None:
        """Refresh process info (CPU, memory, uptime) every second."""
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
    # actions: box navigation and editing
    # ------------------------------------------------------------------ #
    @property
    def _dash(self):
        """The dashboard itself (the bottom-most screen).

        App.query only searches the current top screen; while the editor or a dialog is open, dashboard widgets (log, status bar, boxes) must be looked up on the bottom screen, otherwise kcauto output is lost during editing and store notifications cannot find the status bar.
        """
        return self.screen_stack[0]

    def _modal_open(self) -> bool:
        """While any screen (dialog or editor) is above the dashboard, dashboard shortcuts are all disabled."""
        return len(self.screen_stack) > 1

    def _focused_card(self) -> ModuleCard | None:
        focused = self.focused
        return focused if isinstance(focused, ModuleCard) else None

    def _focused_log(self) -> bool:
        return isinstance(self.focused, LogBox)

    def action_focus_card(self, module: str) -> None:
        if self._modal_open():
            return
        self._dash.query_one(f"#card-{module}", ModuleCard).focus()

    def action_move_focus(self, dx: int, dy: int) -> None:
        if self._modal_open():
            return
        card = self._focused_card()
        if card is None:
            self._dash.query_one(f"#{self._last_card_id}", ModuleCard).focus()
            return
        index = CARDS.index(card.spec)
        columns = self.layout_plan.columns if self.layout_plan else 2
        target_index = move_index(index, dx, dy, columns=columns)
        if target_index == index and self._log_in_direction(dx, dy):
            self._dash.query_one(
                LogBox
            ).focus()  # walked past the edge toward the log → enter the log
            return
        self.action_focus_card(CARDS[target_index].module)

    def _log_in_direction(self, dx: int, dy: int) -> bool:
        """Log on the right: walk right into it; log below: walk down into it; cannot enter when hidden."""
        plan = self.layout_plan
        if plan is None:
            return False
        return (plan.log == LOG_RIGHT and dx > 0) or (plan.log == LOG_BOTTOM and dy > 0)

    def log_arrow(self, dx: int, dy: int, at_top: bool) -> bool:
        """Arrow keys while the log has focus. Returns True = left the log (do not scroll).

        ← always returns to the boxes; when the log is below (or full screen), ↑ at the very top returns too.
        """
        if self._modal_open():
            return False
        plan = self.layout_plan
        full = self._dash.query_one("#main").has_class("log-full")
        leave = dx < 0 or (
            dy < 0
            and at_top
            and (full or (plan is not None and plan.log == LOG_BOTTOM))
        )
        if leave:
            self._leave_log()
        return leave

    def action_toggle_focused(self) -> None:
        if self._modal_open():
            return
        card = self._focused_card()
        if card is not None and card.spec.toggleable:
            self._toggle(card.spec)

    def action_edit_focused(self) -> None:
        if self._modal_open():
            return
        if self._focused_log():
            self.activate_log()
            return
        card = self._focused_card()
        if card is not None:
            self._edit(card.spec)

    def action_choose_language(self) -> None:
        if self._modal_open():
            return
        options = [(f"{name}  ({code})", code) for code, name in i18n.available()]
        self.push_screen(
            ChoiceDialog(
                "Language / 言語 / 語言",
                "The editor uses this language from the next time you open it. "
                "The dashboard stays in English.",
                options,
                i18n.language(),
            ),
            self._language_chosen,
        )

    def _language_chosen(self, result) -> None:
        if result is None or not i18n.set_language(result.value):
            return
        i18n.save_pref(result.value)
        self.notify(
            f"Language: {dict(i18n.available()).get(result.value, result.value)}",
            timeout=2,
        )

    # ------------------------------------------------------------------ #
    # actions: kcauto process
    # ------------------------------------------------------------------ #
    def action_apply_config(self) -> None:
        """Ask for confirmation, then save and (re)start kcauto. Not offered if there are errors."""
        if self._modal_open():
            return
        if self.store.has_errors():
            count = sum(1 for i in self.store.issues() if i.level == "error")
            self.notify(
                f"Config has {count} error(s); kcauto not started",
                severity="error",
                timeout=6,
            )
            return
        self.push_screen(
            ConfirmApply(
                changes=len(self.store.changed_keys()),
                running=self.runner.state is not RunState.STOPPED,
                new_file=self.store.is_new_file,
                file_name=Path(self.store.path).name,
            ),
            self._on_apply_choice,
        )

    def _on_apply_choice(self, go: bool | None) -> None:
        if not go:
            return
        if self.store.has_errors():  # cannot change while the dialog is open; be safe
            return
        if (self.store.changed_keys() or self.store.is_new_file) and not self._save():
            return
        self._spawn(self._do_restart())

    def activate_log(self) -> None:
        """Enter on the log or a click on it: send Enter if kcauto waits for it, otherwise apply."""
        if self._modal_open():
            return
        if self.runner.waiting_enter:
            self._spawn(self._send_enter())
        else:
            self.action_apply_config()

    def action_toggle_debug(self) -> None:
        """Switch debug mode: kcauto gets ``--debug-output`` from its next start on."""
        if self._modal_open():
            return
        self.runner.debug = not self.runner.debug
        prefs.save_value("debug", self.runner.debug)
        bar = self._dash.query_one(StatusBar)
        bar.debug = self.runner.debug
        bar.refresh_from(self.store)
        message = "Debug output on" if self.runner.debug else "Debug output off"
        if self.runner.state is not RunState.STOPPED:
            message += ": applies when kcauto is (re)started (Enter on the log)"
        self.notify(message, timeout=4)

    def action_toggle_pause(self) -> None:
        if self._modal_open():
            return
        if self.runner.toggle_pause() is None:
            self.notify("kcauto is not running", timeout=2)

    def action_focus_log(self) -> None:
        if self._modal_open():
            return
        main = self._dash.query_one("#main")
        if self.layout_plan is not None and self.layout_plan.log == LOG_HIDDEN:
            if main.has_class("log-full"):
                self._leave_log()
            else:
                self._reveal_log()
        else:
            self._dash.query_one(LogBox).focus()

    def action_leave_log(self) -> None:
        if self._modal_open():
            return
        main = self._dash.query_one("#main")
        if main.has_class("log-full") or self._focused_log():
            self._leave_log()

    def _reveal_log(self) -> None:
        """Make the log visible and focus it (full-screen log when the layout has no room)."""
        if self._modal_open():
            return
        main = self._dash.query_one("#main")
        if self.layout_plan is not None and self.layout_plan.log == LOG_HIDDEN:
            main.add_class("log-full")
        log = self._dash.query_one(LogBox)

        def focus_log() -> None:
            log.sync()
            log.focus()

        self.call_after_refresh(focus_log)

    def _leave_log(self) -> None:
        self._dash.query_one("#main").remove_class("log-full")
        self._dash.query_one(f"#{self._last_card_id}", ModuleCard).focus()
        self._sync_log_later()

    def _spawn(self, coroutine) -> None:
        self.run_worker(self._guarded(coroutine), group="runner", exclusive=False)

    async def _guarded(self, coroutine) -> None:
        """Unexpected exceptions inside a worker are only written to the log; they never end the whole UI."""
        try:
            await coroutine
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._on_runner_log(LOG_SYSTEM, f"Internal error: {exc!r}")

    async def _do_restart(self) -> None:
        async with self._runner_lock:
            await self.runner.restart()

    async def _send_enter(self) -> None:
        await self.runner.send_enter()

    async def _shutdown(self) -> None:
        try:
            async with self._runner_lock:
                await self.runner.stop()
        finally:
            self.exit()  # leave even if stopping failed; on_unmount will kill again as a safeguard

    # ------------------------------------------------------------------ #
    # quit
    # ------------------------------------------------------------------ #
    def action_request_quit(self) -> None:
        if self._modal_open():
            return
        dirty = bool(self.store.changed_keys())
        running = self.runner.state is not RunState.STOPPED
        if not dirty and not running:
            self.exit()
            return
        self.push_screen(
            ConfirmQuit(dirty=dirty, running=running), self._on_quit_choice
        )

    def _on_quit_choice(self, choice: str | None) -> None:
        if choice == "save":
            if self._save():
                self._spawn(self._shutdown())
        elif choice == "discard":
            self._spawn(self._shutdown())

    # ------------------------------------------------------------------ #
    # implementation
    # ------------------------------------------------------------------ #
    def _toggle(self, spec: CardSpec) -> None:
        current = self.store.get(spec.enabled_key)
        self.store.set(
            spec.enabled_key, (not current) if isinstance(current, bool) else True
        )

    def _edit(self, spec: CardSpec) -> None:
        self.push_screen(EditorScreen(self.store, spec.module))

    def _save(self) -> bool:
        try:
            path = self.store.save()
        except ConfigValidationError as exc:
            first = exc.issues[0].message
            self.notify(
                f"{len(exc.issues)} error(s), not saved: {first}",
                severity="error",
                timeout=6,
            )
            return False
        except OSError as exc:
            self.notify(f"Write failed: {exc}", severity="error", timeout=6)
            return False
        self.notify(f"Saved {path.name}", timeout=2)
        return True

    # ------------------------------------------------------------------ #
    # mouse events (sent by Box)
    # ------------------------------------------------------------------ #
    @on(Box.Toggled)
    def _box_toggled(self, event: Box.Toggled) -> None:
        if isinstance(event.box, ModuleCard) and not self._modal_open():
            self._toggle(event.box.spec)

    @on(Box.Activated)
    def _box_activated(self, event: Box.Activated) -> None:
        if isinstance(event.box, ModuleCard) and not self._modal_open():
            self._edit(event.box.spec)
