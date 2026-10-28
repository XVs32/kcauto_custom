"""btop 風格方框:圓角邊框、標題嵌在上緣、右下角開關、可聚焦、可點擊。

互動
  * 單擊:聚焦。
  * 點右下角的 ON/OFF:切換(送出 ``Box.Toggled``)。
  * 雙擊:開啟編輯(送出 ``Box.Activated``)。Enter 由 App 層處理。
"""
from __future__ import annotations

from textual import events
from textual.message import Message
from textual.widgets import Static

ON_MARKUP = "[#98c379]● ON[/]"
OFF_MARKUP = "[#7f848e]○ OFF[/]"


class Box(Static, can_focus=True):
    # 右下角開關的點擊範圍(字元數)。subtitle 由 Textual 畫在下邊框、靠右。
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
        """更新開關外觀;不可切換的方框恆為 on(不顯示開關)。"""
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
