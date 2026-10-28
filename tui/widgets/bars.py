"""頂部狀態列與底部快捷鍵提示列。"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from rich.text import Text
from textual.widgets import Static

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


def hint_text() -> Text:
    text = Text(no_wrap=True, overflow="ellipsis")
    for key, desc in HINTS:
        text.append(key, style=KEY_STYLE)
        text.append(f" {desc}  ", style=DESC_STYLE)
    return text


class HintBar(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(hint_text(), **kwargs)


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

    def refresh_from(self, store: ConfigStore) -> None:
        issues = store.issues()
        errors = sum(1 for i in issues if i.level == "error")
        warnings = sum(1 for i in issues if i.level in ("warning", "danger"))

        state_style = STATE_STYLES.get(self.run_state, DIM)
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(" kcauto_custom  ", style="bold")
        text.append("● ", style=state_style)
        text.append(self.run_state.upper(), style=state_style)

        if self.waiting_enter:
            text.append("  ⏎ 等待 Enter", style="bold #e5c07b")

        if self.sample is not None:
            s = self.sample
            text.append(
                f"  {fmt_duration(s.uptime)} "
                f"{sparkline(self.cpu_history, 100.0, 8)} {s.cpu:.0f}% "
                f"{fmt_bytes(s.rss)}",
                style=DESC_STYLE,
            )

        text.append("  │  ", style=DIM)
        mode = store.get("general.interaction_mode")
        jst = store.get("general.jst_offset")
        jst_text = f"{jst:+d}" if isinstance(jst, int) and not isinstance(jst, bool) else str(jst)
        text.append(f"{mode} JST{jst_text}", style=DESC_STYLE)

        text.append("  │  ", style=DIM)
        name = Path(store.path).name
        dirty = bool(store.changed_keys())
        text.append(name + ("*" if dirty else ""),
                    style="bold #e5c07b" if dirty else DESC_STYLE)

        if errors:
            text.append(f"  ✖ {errors}", style="bold #e06c75")
        if warnings:
            text.append(f"  ⚠ {warnings}", style="#e5c07b")
        self.update(text)
