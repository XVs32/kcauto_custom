"""Parsing and formatting of scheduler.rules strings.

Format (Ch5): ``condition:value:action:module`` or ``condition:value:action:module:extra``
For example: ``time:0230:stop:kcauto``, ``sorties_run:15:stop:combat``

The CUI only handles the "structure" (4-5 non-empty fields) and does not restrict the valid values of condition / action / module, because kcauto itself decides them; unknown values are always kept and never rewritten.
"""

from __future__ import annotations

from ..i18n import t
from typing import NamedTuple, Optional


class SchedulerRule(NamedTuple):
    condition: str
    value: str
    action: str
    module: str
    extra: Optional[str] = None

    def format(self) -> str:
        parts = [self.condition, self.value, self.action, self.module]
        if self.extra is not None:
            parts.append(self.extra)
        return ":".join(parts)


def parse_rule(text: str) -> SchedulerRule:
    """Parse a rule string; raise ValueError when the format is wrong."""
    if not isinstance(text, str):
        raise ValueError(t("rule must be a string"))
    parts = text.split(":")
    if len(parts) not in (4, 5):
        raise ValueError(
            t(
                "rule must be condition:value:action:module[:extra]; it has {n} fields",
                n=len(parts),
            )
        )
    names = ("condition", "value", "action", "module", "extra")
    for name, part in zip(names, parts):
        if part.strip() == "":
            raise ValueError(t("field {name} cannot be empty", name=name))
    return SchedulerRule(*[p.strip() for p in parts])


def check_rule(item: object) -> Optional[str]:
    """For Field.item_check: returns None when valid, otherwise an error message."""
    try:
        parse_rule(item)  # type: ignore[arg-type]
    except ValueError as exc:
        return str(exc)
    return None
