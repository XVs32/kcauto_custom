"""頂部狀態列與底部快捷鍵提示列。"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from rich.text import Text
from textual.widgets import Static

from ..layout import fit_segments
from ..procstats import fmt_bytes, fmt_duration, sparkline
from ..runner import ProcSample
from ..store import ConfigStore

KEY_STYLE = "bold #e5c07b"
DESC_STYLE = "#9aa0a6"
DIM = "#6b7280"

HINTS: tuple[tuple[str, str], ...] = (
    ("←↑↓→", "move"),
    ("space", "toggle"),
    ("enter", "edit"),
    ("a", "apply"),
    ("b", "pause"),
    ("k", "stop"),
    ("l", "log"),
    ("w", "save"),
    ("q", "quit"),
)

STATE_STYLES = {
    "running": "#98c379",
    "paused": "#e5c07b",
    "stopped": DIM,
}


# 一行放不下時,依序丟掉(先丟最不重要的)
HINT_DROP_ORDER = ("toggle", "move", "pause", "log", "edit", "stop", "apply")
STATUS_DROP_ORDER = ("title", "mode", "spark", "mem", "uptime", "cpu")


def hint_text(width: int = 0) -> Text:
    """底部提示列;視窗太窄時丟掉次要的提示,保留存檔 / 離開。"""
    lengths = [(desc, len(key) + len(desc) + 3) for key, desc in HINTS]
    kept = fit_segments(lengths, HINT_DROP_ORDER, width - 1 if width else 0)
    text = Text(no_wrap=True, overflow="ellipsis")
    for key, desc in HINTS:
        if desc in kept:
            text.append(key, style=KEY_STYLE)
            text.append(f" {desc}  ", style=DESC_STYLE)
    return text


class HintBar(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(hint_text(), **kwargs)

    def on_resize(self, event) -> None:
        self.update(hint_text(event.size.width))


class StatusBar(Static):
    """執行狀態、行程資訊、操作模式、設定檔與驗證問題數。

    由左到右依重要性排列,視窗太窄時右側會被截斷。
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.run_state = "stopped"
        self.waiting_enter = False
        self.sample: Optional[ProcSample] = None
        self.cpu_history: Sequence[float] = ()
        self.config_store: Optional[ConfigStore] = None

    def set_run(self, state: str, waiting_enter: bool) -> None:
        self.run_state = state
        self.waiting_enter = waiting_enter
        if state == "stopped":
            self.sample = None
            self.cpu_history = ()

    def set_process(self, sample: Optional[ProcSample],
                    cpu_history: Sequence[float] = ()) -> None:
        self.sample = sample
        self.cpu_history = cpu_history

    def on_resize(self, event) -> None:
        if self.config_store is not None:
            self.refresh_from(self.config_store)

    def refresh_from(self, store: ConfigStore) -> None:
        """依目前寬度組出狀態列;太窄時先丟次要資訊,檔名(含 *)與問題數永遠保留。"""
        self.config_store = store
        issues = store.issues()
        errors = sum(1 for i in issues if i.level == "error")
        warnings = sum(1 for i in issues if i.level in ("warning", "danger"))

        parts: list[tuple[str, Text]] = []

        def seg(name: str, *pieces: tuple[str, str]) -> None:
            t = Text(no_wrap=True)
            for piece, style in pieces:
                t.append(piece, style=style)
            parts.append((name, t))

        state_style = STATE_STYLES.get(self.run_state, DIM)
        seg("title", (" kcauto_custom  ", "bold"))
        seg("state", ("● ", state_style), (self.run_state.upper(), state_style))
        if self.waiting_enter:
            seg("waiting", ("  ⏎ 等待 Enter", "bold #e5c07b"))
        if self.sample is not None:
            s = self.sample
            seg("uptime", (f"  {fmt_duration(s.uptime)}", DESC_STYLE))
            seg("spark", (f" {sparkline(self.cpu_history, 100.0, 8)}", DESC_STYLE))
            seg("cpu", (f" {s.cpu:.0f}%", DESC_STYLE))
            seg("mem", (f" {fmt_bytes(s.rss)}", DESC_STYLE))

        mode = store.get("general.interaction_mode")
        jst = store.get("general.jst_offset")
        jst_text = f"{jst:+d}" if isinstance(jst, int) and not isinstance(jst, bool) else str(jst)
        seg("mode", ("  │  ", DIM), (f"{mode} JST{jst_text}", DESC_STYLE))

        name = Path(store.path).name
        dirty = bool(store.changed_keys())
        seg("file", ("  │  ", DIM),
            (name + ("*" if dirty else ""), "bold #e5c07b" if dirty else DESC_STYLE))
        if errors:
            seg("errors", (f"  ✖ {errors}", "bold #e06c75"))
        if warnings:
            seg("warnings", (f"  ⚠ {warnings}", "#e5c07b"))

        kept = fit_segments([(n, t.cell_len) for n, t in parts], STATUS_DROP_ORDER,
                            self.size.width)
        text = Text(no_wrap=True, overflow="ellipsis")
        for n, t in parts:
            if n in kept:
                text.append_text(t)
        self.update(text)
