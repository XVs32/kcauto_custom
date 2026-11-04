"""btop-style box: rounded border, title embedded in the top edge, switch at the bottom right, focusable and clickable.

Interaction
  * Click on a box that does not have the focus: focus it.
  * Click on a box that already has the focus: open editing, same as Enter (sends ``Box.Activated``).
    The click that merely gave it the focus does not count (see ``CLICK_FOCUS_GRACE``); a double click
    also opens editing. Enter itself is handled by the App.
  * Click on the ON/OFF switch (bottom border, right): toggle (sends ``Box.Toggled``) - only the switch
    and a column or so around it, not the rest of the box.
"""

from __future__ import annotations

import time

from textual import events
from textual.message import Message
from textual.widgets import Static

from ..modules import in_toggle_zone

ON_MARKUP = "[#98c379]● ON[/]"
OFF_MARKUP = "[#7f848e]○ OFF[/]"


class Box(Static, can_focus=True):
    # The focus arrives on mouse-down, a moment before the click, so a click only opens editing when the
    # box had the focus for at least this long (seconds).
    CLICK_FOCUS_GRACE = 0.4

    class Toggled(Message):
        def __init__(self, box: "Box") -> None:
            super().__init__()
            self.box = box

        @property
        def control(self) -> "Box":
            return self.box

    class Activated(Message):
        def __init__(self, box: "Box") -> None:
            super().__init__()
            self.box = box

        @property
        def control(self) -> "Box":
            return self.box

    def __init__(
        self,
        *,
        box_title: str,
        toggleable: bool = False,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__("", id=id, classes=classes)
        self.border_title = box_title
        self.toggleable = toggleable
        self.is_on = True
        self._focused_at = 0.0

    def on_focus(self, event: events.Focus) -> None:
        self._focused_at = time.monotonic()

    def set_state(self, on: bool) -> None:
        """Update the switch appearance; a box that cannot be toggled is always on (no switch is shown)."""
        self.is_on = on
        self.set_class(not on, "off")
        if self.toggleable:
            self.border_subtitle = ON_MARKUP if on else OFF_MARKUP

    def _in_toggle_zone(self, event: events.Click) -> bool:
        # ``self.size`` excludes the border, so work from the outer region and screen coordinates.
        region = self.region
        return self.toggleable and in_toggle_zone(
            event.screen_x - region.x,
            event.screen_y - region.y,
            region.width,
            region.height,
            self.is_on,
        )

    def on_click(self, event: events.Click) -> None:
        if self._in_toggle_zone(event):
            event.stop()
            self.post_message(self.Toggled(self))
            return
        was_focused = (
            self.has_focus
            and time.monotonic() - self._focused_at >= self.CLICK_FOCUS_GRACE
        )
        self.focus()
        if was_focused or getattr(event, "chain", 1) >= 2:
            self.post_message(self.Activated(self))
