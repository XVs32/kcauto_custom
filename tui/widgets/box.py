"""btop-style box: rounded border, title embedded in the top edge, switch at the bottom right, focusable and clickable.

Interaction
  * Single click: focus.
  * Click ON/OFF at the bottom right: toggle (sends ``Box.Toggled``).
  * Double click: open editing (sends ``Box.Activated``). Enter is handled by the App.
"""

from __future__ import annotations

from textual import events
from textual.message import Message
from textual.widgets import Static

ON_MARKUP = "[#98c379]● ON[/]"
OFF_MARKUP = "[#7f848e]○ OFF[/]"


class Box(Static, can_focus=True):
    # click area (in characters) of the bottom-right switch. Textual draws the subtitle on the bottom border, right-aligned.
    TOGGLE_HIT_WIDTH = 12

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

    def set_state(self, on: bool) -> None:
        """Update the switch appearance; a box that cannot be toggled is always on (no switch is shown)."""
        self.is_on = on
        self.set_class(not on, "off")
        if self.toggleable:
            self.border_subtitle = ON_MARKUP if on else OFF_MARKUP

    def _in_toggle_zone(self, event: events.Click) -> bool:
        size = self.size
        return (
            self.toggleable
            and event.y >= size.height - 1
            and event.x >= size.width - self.TOGGLE_HIT_WIDTH
        )

    def on_click(self, event: events.Click) -> None:
        if self._in_toggle_zone(event):
            event.stop()
            self.post_message(self.Toggled(self))
            return
        self.focus()
        if getattr(event, "chain", 1) >= 2:
            self.post_message(self.Activated(self))
