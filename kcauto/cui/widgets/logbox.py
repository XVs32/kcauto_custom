"""Log box: shows kcauto output and the CUI's own messages.

Design notes
  * Keeps its own bounded history (``history``). While the box is hidden (no room in the layout) nothing is written to the RichLog, because a hidden RichLog buffers writes without limit; when it is shown again or the window width changes, it is redrawn from the history (which also recomputes word wrap for the new width).
  * Output lines are coloured by the ANSI colour convention (see ``ansi.py``).
  * While the box has focus, ↑ ↓ and the paging keys scroll the log; ← returns to the boxes (when the log is below, ↑ at the very top returns too).
    Pressing an arrow key toward the log from the boxes enters the log (see ``KcautoCui.action_move_focus``). Esc still works.
"""

from __future__ import annotations

import time
from collections import deque

from rich.text import Text
from textual import events
from textual.binding import Binding
from textual.widgets import RichLog

from ..ansi import parse_ansi
from ..runner import LOG_OUTPUT

BUFFER_LINES = 3000
SYSTEM_STYLE = "italic #7f848e"
REWRAP_DELAY = 0.2  # redraw delay (seconds) when the window is resized, to avoid redrawing continuously while dragging


class LogBox(RichLog, can_focus=True):
    BINDINGS = [
        Binding("up", "log_arrow(0,-1)", show=False),
        Binding("down", "log_arrow(0,1)", show=False),
        Binding("left", "log_arrow(-1,0)", show=False),
        Binding("right", "log_arrow(1,0)", show=False),
    ]

    # A click that merely gives the log the focus must not apply; the focus arrives on mouse-down, a moment
    # before the click, so only a click on a log that has had the focus for a while counts.
    CLICK_FOCUS_GRACE = 0.4

    def on_focus(self, event: events.Focus) -> None:
        self._focused_at = time.monotonic()

    def on_click(self, event: events.Click) -> None:
        if event.chain != 1 or not self.has_focus:
            return
        if time.monotonic() - self._focused_at < self.CLICK_FOCUS_GRACE:
            return
        activate = getattr(self.app, "activate_log", None)
        if activate is not None:
            event.stop()
            activate()

    def action_log_arrow(self, dx: int, dy: int) -> None:
        """Arrow keys: leave the log when appropriate by handing over to the App, otherwise scroll the log."""
        leave = getattr(self.app, "log_arrow", None)
        if leave is not None and leave(dx, dy, self.scroll_y <= 0):
            return
        if dy < 0:
            self.scroll_up(animate=False)
        elif dy > 0:
            self.scroll_down(animate=False)

    def __init__(self, **kwargs) -> None:
        super().__init__(
            max_lines=BUFFER_LINES,
            wrap=True,
            markup=False,
            highlight=False,
            auto_scroll=True,
            **kwargs,
        )
        self.history: deque[Text] = deque(maxlen=BUFFER_LINES)
        self._stale = False
        self._rewrap_timer = None
        self._last_width = 0
        self._focused_at = 0.0

    # ------------------------------------------------------------------ #
    # writing
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_text(kind: str, text: str) -> Text:
        if kind == LOG_OUTPUT:
            line = Text(no_wrap=False)
            for chunk, style in parse_ansi(text):
                line.append(chunk, style=style or None)
            return line
        return Text(f"── {text}", style=SYSTEM_STYLE)

    def add(self, kind: str, text: str) -> None:
        line = self.to_text(kind, text)
        self.history.append(line)
        if self._visible():
            self.write(line)
        else:
            self._stale = True

    def plain_lines(self) -> list[str]:
        return [line.plain for line in self.history]

    # ------------------------------------------------------------------ #
    # display / redraw
    # ------------------------------------------------------------------ #
    def _visible(self) -> bool:
        return self.display and self.size.width > 0

    def sync(self) -> None:
        """Call after a layout change: if the box is now visible and its content is stale, redraw from the history."""
        if self._stale and self._visible():
            self._rewrite()

    def _rewrite(self) -> None:
        self.clear()
        for line in self.history:
            self.write(line)
        self._stale = False
        self._last_width = self.size.width

    def on_resize(self, event) -> None:
        width = event.size.width
        if width <= 0 or width == self._last_width:
            return
        self._last_width = width
        if not self.history:
            return
        if self._rewrap_timer is not None:
            self._rewrap_timer.stop()
        self._rewrap_timer = self.set_timer(REWRAP_DELAY, self._rewrite)
