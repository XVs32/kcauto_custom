"""Module box on the dashboard: shows a summary of the config values and reflects the enabled state."""

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
        """Redraw the content and the switch state from the current values."""
        if self.spec.toggleable:
            on = values.get(self.spec.enabled_key) is True
        else:
            on = True

        text = Text()
        for index, (line, style) in enumerate(summarize(self.spec.module, values)):
            if index:
                text.append("\n")
            # When the module is disabled the whole card turns grey, so it does not look like it is still running
            text.append(line, style=(style or None) if on else OFF_STYLE)
        self.update(text)
        self.set_state(on)
