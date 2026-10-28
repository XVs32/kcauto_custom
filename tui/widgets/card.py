"""儀表板上的模組方框:依設定值顯示摘要,並反映 enabled 狀態。"""
from __future__ import annotations

from typing import Any, Mapping

from rich.text import Text

from ..modules import CardSpec, hotkey_markup
from ..summaries import summarize
from .box import Box

OFF_STYLE = "#6b7280"


class ModuleCard(Box):
    def __init__(self, spec: CardSpec) -> None:
        super().__init__(
            box_title=hotkey_markup(spec.label, spec.hotkey),
            toggleable=spec.toggleable,
            id=spec.card_id,
            classes=f"mod-{spec.module}",
        )
        self.spec = spec

    def show(self, values: Mapping[str, Any]) -> None:
        """依目前設定值重畫內容與開關狀態。"""
        if self.spec.toggleable:
            on = values.get(self.spec.enabled_key) is True
        else:
            on = True

        text = Text()
        for index, (line, style) in enumerate(summarize(self.spec.module, values)):
            if index:
                text.append("\n")
            # 模組停用時整張卡片改成灰色,避免「看起來還在運作」
            text.append(line, style=(style or None) if on else OFF_STYLE)
        self.update(text)
        self.set_state(on)
