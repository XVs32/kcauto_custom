"""頂部狀態列與底部快捷鍵提示列。"""
from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.widgets import Static

from ..store import ConfigStore

KEY_STYLE = "bold #e5c07b"
DESC_STYLE = "#9aa0a6"
DIM = "#6b7280"

HINTS: tuple[tuple[str, str], ...] = (
    ("←↑↓→", "move"),
    ("c e p …", "jump"),
    ("space", "toggle"),
    ("enter", "edit"),
    ("w", "save"),
    ("q", "quit"),
)


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
    """顯示執行狀態、操作模式、設定檔與驗證問題數。

    runner 狀態在階段 3 接上;目前固定顯示 STOPPED。
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.run_state = "stopped"

    def refresh_from(self, store: ConfigStore) -> None:
        issues = store.issues()
        errors = sum(1 for i in issues if i.level == "error")
        warnings = sum(1 for i in issues if i.level in ("warning", "danger"))

        dot_style = {"running": "#98c379", "paused": "#e5c07b"}.get(
            self.run_state, DIM
        )
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(" kcauto_custom  ", style="bold")
        text.append("● ", style=dot_style)
        text.append(self.run_state.upper(), style=dot_style)
        text.append("  ")

        mode = store.get("general.interaction_mode")
        jst = store.get("general.jst_offset")
        jst_text = f"{jst:+d}" if isinstance(jst, int) and not isinstance(jst, bool) else str(jst)
        text.append(f"{mode}  JST{jst_text}", style=DESC_STYLE)

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
