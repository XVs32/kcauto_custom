"""日誌方框:顯示 kcauto 的輸出與 CUI 自己的訊息。

設計重點
  * 自己保留一份有上限的歷史(``history``)。方框被隱藏(版面放不下)時不寫進 RichLog,
    因為隱藏中的 RichLog 會把寫入暫存起來而無上限成長;重新顯示或視窗寬度改變時,
    再從歷史重繪(同時讓自動換行依新寬度重算)。
  * 輸出行依 ANSI 顏色約定上色(見 ``ansi.py``)。
  * 方框取得焦點時,方向鍵/翻頁鍵用來捲動日誌;Esc 回到方框區。
"""
from __future__ import annotations

from collections import deque

from rich.text import Text
from textual.widgets import RichLog

from ..ansi import parse_ansi
from ..runner import LOG_OUTPUT

BUFFER_LINES = 3000
SYSTEM_STYLE = "italic #7f848e"
REWRAP_DELAY = 0.2     # 視窗縮放時的重繪延遲(秒),避免拖曳過程中連續重繪


class LogBox(RichLog, can_focus=True):
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

    # ------------------------------------------------------------------ #
    # 寫入
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
    # 顯示 / 重繪
    # ------------------------------------------------------------------ #
    def _visible(self) -> bool:
        return self.display and self.size.width > 0

    def sync(self) -> None:
        """版面變動後呼叫:若方框現在可見且內容過期,從歷史重繪。"""
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
