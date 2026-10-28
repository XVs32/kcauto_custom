"""沙盒用的 Textual / Rich 極簡替身。

只在「沒有安裝 textual」時才會被 ``install()`` 啟用,目的不是模擬畫面,
而是讓編輯器的對話框與元件的「邏輯」(按鈕、清單、滾輪、確定/取消)能在沒有
Textual 的環境真的被執行,抓出 AttributeError 之類的低級錯誤。
真正的畫面行為仍以 tests/test_editor_ui.py(需要 Textual)為準。
"""
from __future__ import annotations

import re
import sys
import types
import unicodedata
from types import SimpleNamespace

STATE = SimpleNamespace(focused=None)


def _cells(text: str) -> int:
    return sum(0 if unicodedata.combining(c) else
               2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


class Text:
    def __init__(self, text: str = "", style: str = "", **_):
        self.plain = text
        self.style = style

    def append(self, piece, style=None):
        self.plain += piece.plain if isinstance(piece, Text) else piece
        return self

    def append_text(self, other):
        self.plain += other.plain
        return self

    def pad_right(self, n):
        self.plain += " " * max(0, n)

    def stylize(self, *_a, **_k):
        pass

    @property
    def cell_len(self):
        return _cells(self.plain)

    def __str__(self):
        return self.plain


class Message:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class Widget:
    def __init_subclass__(cls, can_focus=None, **kw):
        super().__init_subclass__()

    def __init__(self, *children, id=None, classes=None, **_):
        self.id = id
        self.classes = classes
        self.children = list(children)
        self.styles = SimpleNamespace()
        self.size = SimpleNamespace(width=60, height=10)
        self.has_focus = False
        self.posted: list = []
        self.display = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def refresh(self, *a, **k):
        pass

    def focus(self):
        STATE.focused = self
        return self

    def post_message(self, message):
        self.posted.append(message)
        return True

    def set_class(self, *a):
        pass


class Static(Widget):
    def __init__(self, content="", *, id=None, classes=None, **kw):
        super().__init__(id=id, classes=classes)
        self.content = content

    def update(self, content=""):
        self.content = content


class Input(Widget):
    class Changed(Message):
        def __init__(self, input, value):
            super().__init__()
            self.input, self.value = input, value

    class Submitted(Message):
        def __init__(self, input, value):
            super().__init__()
            self.input, self.value = input, value

    def __init__(self, value="", *, placeholder="", id=None, **kw):
        super().__init__(id=id)
        self.value = value
        self.cursor_position = 0


class TextArea(Widget):
    def __init__(self, text="", *, id=None, **kw):
        super().__init__(id=id)
        self.text = text


class Screen(Widget):
    def __init__(self, *a, **k):
        super().__init__()
        self.dismissed = "UNSET"
        self.app = SimpleNamespace(notify=lambda *a, **k: None)
        self._all: list = []
        self._by_id: dict = {}

    @property
    def focused(self):
        return STATE.focused

    def dismiss(self, result=None):
        self.dismissed = result

    def set_interval(self, *a, **k):
        pass

    def query_one(self, selector, expect=None):
        if isinstance(selector, str):
            return self._by_id[selector.lstrip("#")]
        for w in self._all:
            if isinstance(w, selector):
                return w
        raise KeyError(selector)

    def query(self, selector):
        return [w for w in self._all if isinstance(w, selector)]


class ModalScreen(Screen):
    def __class_getitem__(cls, item):
        return cls


_INSTALLED: list[str] = []


def _module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    _INSTALLED.append(name)
    return mod


def uninstall() -> None:
    """匯入完被測模組後移除替身,避免其他測試誤以為有安裝 textual。"""
    for name in _INSTALLED:
        sys.modules.pop(name, None)
    _INSTALLED.clear()


def install() -> bool:
    """啟用替身。已經有真的 textual 時什麼都不做,回傳 False。"""
    try:
        import textual  # noqa: F401
        return False
    except ImportError:
        pass

    class Binding:
        def __init__(self, key, action, description="", show=True, **kw):
            self.key, self.action = key, action

    class Event(Message):
        pass

    events = _module("textual.events",
                     Click=Event, MouseEvent=Event, MouseScrollUp=Event,
                     MouseScrollDown=Event, Resize=Event, DescendantFocus=Event, Key=Event)
    containers = _module("textual.containers", Horizontal=type("Horizontal", (Widget,), {}),
                         Vertical=type("Vertical", (Widget,), {}),
                         VerticalScroll=type("VerticalScroll", (Widget,), {}),
                         Grid=type("Grid", (Widget,), {}))

    def on(*_a, **_k):
        return lambda f: f

    _module("rich")
    _module("rich.text", Text=Text)
    textual = _module("textual", events=events, on=on)
    textual.__path__ = []
    _module("textual.app", App=Widget, ComposeResult=object)
    _module("textual.binding", Binding=Binding)
    _module("textual.message", Message=Message)
    _module("textual.widget", Widget=Widget)
    _module("textual.widgets", Static=Static, Input=Input, TextArea=TextArea)
    _module("textual.screen", Screen=Screen, ModalScreen=ModalScreen)
    return True


# ---------------------------------------------------------------------- #
# 測試輔助
# ---------------------------------------------------------------------- #
def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def handler_name(message) -> str:
    """PickList.Chosen → on_pick_list_chosen(與 Textual 的規則相同)。"""
    qual = type(message).__qualname__
    return "on_" + "_".join(snake(part) for part in qual.split("."))


def mount(screen):
    """執行 compose(),把產生的元件登記起來,再呼叫 on_mount()。"""
    def walk(widget):
        screen._all.append(widget)
        if widget.id:
            screen._by_id[widget.id] = widget
        for child in widget.children:
            walk(child)

    for widget in screen.compose():
        walk(widget)
    if hasattr(screen, "on_mount"):
        screen.on_mount()
    return screen


def pump(screen, limit=50):
    """把子元件 post 出來的訊息交給對話框的處理器(模擬訊息往上冒泡)。"""
    for _ in range(limit):
        pending = [(w, m) for w in screen._all for m in w.posted]
        if not pending:
            return
        for w, m in pending:
            w.posted.remove(m)
            handler = getattr(screen, handler_name(m), None)
            if handler is not None:
                handler(m)
