"""設定驗證:單欄位(委派給 Field.validate)與跨欄位規則。

嚴重程度(``Issue.level``):
  * ``error``   — 值不合法或會讓 kcauto 無法運作;「套用並重啟」會被擋下。
  * ``warning`` — 可存檔、可套用,但很可能不是使用者想要的。
  * ``danger``  — 合法但高風險(例如大破進擊),修改時需要二次確認。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .fields import COMBINED_FLEET_MODES, SCHEMA

ERROR = "error"
WARNING = "warning"
DANGER = "danger"


@dataclass(frozen=True)
class Issue:
    level: str
    keys: tuple[str, ...]
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {', '.join(self.keys)}: {self.message}"


def validate_field(key: str, value: Any) -> list[Issue]:
    """驗證單一欄位。不在 schema 內的 key 視為未知欄位,不產生問題。"""
    field = SCHEMA.get(key)
    if field is None:
        return []
    issues = [Issue(ERROR, (key,), msg) for msg in field.validate(value)]
    if field.danger and not issues and value:
        issues.append(Issue(DANGER, (key,), f"{field.label}:此設定具有風險"))
    return issues


def validate_cross(values: Mapping[str, Any]) -> list[Issue]:
    """跨欄位規則。欄位本身不合法時略過相關規則,避免重複或誤報。"""
    issues: list[Issue] = []
    get = values.get

    # 演習不可與聯合艦隊同時使用(Ch5: pvp.enabled)
    if get("pvp.enabled") is True and get("combat.fleet_mode") in COMBINED_FLEET_MODES:
        # 出擊模組沒開時,聯合艦隊設定不會生效,降為警告
        level = ERROR if get("combat.enabled") is True else WARNING
        issues.append(Issue(
            level, ("pvp.enabled", "combat.fleet_mode"),
            "出擊艦隊為聯合艦隊時不可啟用演習",
        ))

    # 基地航空隊:啟用的隊伍應該有目標節點,有目標節點的隊伍應該被啟用
    groups = get("combat.lbas_groups")
    if isinstance(groups, list):
        active = {str(g) for g in groups}
        for n in (1, 2, 3):
            key = f"combat.lbas_group_{n}_nodes"
            nodes = get(key)
            if not isinstance(nodes, list):
                continue
            if str(n) in active and len(nodes) == 0:
                issues.append(Issue(
                    WARNING, ("combat.lbas_groups", key),
                    f"第 {n} 基地航空隊已啟用,但沒有設定目標節點",
                ))
            elif str(n) not in active and len(nodes) > 0:
                issues.append(Issue(
                    WARNING, ("combat.lbas_groups", key),
                    f"第 {n} 基地航空隊設定了目標節點,但沒有啟用",
                ))

    # 同時要求「撤退」與「強行進擊」同一節點,語意互相矛盾
    retreat, push = get("combat.retreat_points"), get("combat.push_nodes")
    if isinstance(retreat, list) and isinstance(push, list):
        both = sorted({str(x) for x in retreat} & {str(x) for x in push})
        if both:
            issues.append(Issue(
                WARNING, ("combat.retreat_points", "combat.push_nodes"),
                "節點 " + "、".join(both) + " 同時出現在撤退與強行進擊",
            ))

    # 啟發式提醒(非 Ch5 明文規定,僅 warning):修理門檻高於撤退門檻時,
    # 剛因撤退而回港的艦娘損傷等級低於修理門檻,下次出擊前不會被修理
    retreat_limit, repair_limit = get("combat.retreat_limit"), get("combat.repair_limit")
    if (
        isinstance(retreat_limit, int) and isinstance(repair_limit, int)
        and not isinstance(retreat_limit, bool) and not isinstance(repair_limit, bool)
        and repair_limit > retreat_limit
    ):
        issues.append(Issue(
            WARNING, ("combat.retreat_limit", "combat.repair_limit"),
            "修理損傷等級高於撤退損傷等級,撤退的艦娘可能不會被修理",
        ))

    return issues


def validate_all(values: Mapping[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for key, value in values.items():
        issues.extend(validate_field(key, value))
    issues.extend(validate_cross(values))
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level == ERROR for i in issues)
