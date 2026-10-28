"""scheduler.rules 字串的解析與格式化。

格式(Ch5):``condition:value:action:module`` 或 ``condition:value:action:module:extra``
例如:``time:0230:stop:kcauto``、``sorties_run:15:stop:combat``

CUI 只負責「結構」(4~5 個非空欄位),不限制 condition / action / module
的合法值,因為這些值由 kcauto 本體決定;未知值一律保留,不會被改寫。
"""
from __future__ import annotations

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
    """解析規則字串;格式不合時丟出 ValueError。"""
    if not isinstance(text, str):
        raise ValueError("規則必須是字串")
    parts = text.split(":")
    if len(parts) not in (4, 5):
        raise ValueError(
            "規則需為 condition:value:action:module[:extra],"
            f"目前有 {len(parts)} 個欄位"
        )
    names = ("condition", "value", "action", "module", "extra")
    for name, part in zip(names, parts):
        if part.strip() == "":
            raise ValueError(f"欄位 {name} 不可為空")
    return SchedulerRule(*[p.strip() for p in parts])


def check_rule(item: object) -> Optional[str]:
    """供 Field.item_check 使用:合法回傳 None,否則回傳錯誤訊息。"""
    try:
        parse_rule(item)  # type: ignore[arg-type]
    except ValueError as exc:
        return str(exc)
    return None
