"""Config validation: single field (delegated to Field.validate) and cross-field rules.

Severity (``Issue.level``):
  * ``error``   — the value is invalid or would stop kcauto from working; "apply and restart" is blocked.
  * ``warning`` — can be saved and applied, but is probably not what the user wants.
  * ``danger``  — valid but high risk (for example advancing with heavily damaged ships); needs a second confirmation when changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..i18n import t
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
    """Validate one field. A key not in the schema is an unknown field and produces no issue."""
    field = SCHEMA.get(key)
    if field is None:
        return []
    issues = [Issue(ERROR, (key,), msg) for msg in field.validate(value)]
    if field.danger and not issues and value:
        issues.append(
            Issue(
                DANGER, (key,), t("{label}: this setting is risky", label=field.label)
            )
        )
    return issues


def validate_cross(values: Mapping[str, Any]) -> list[Issue]:
    """Cross-field rules. Skipped when a field itself is invalid, to avoid duplicate or false reports."""
    issues: list[Issue] = []
    get = values.get

    # PvP cannot be used together with a combined fleet (Ch5: pvp.enabled)
    if get("pvp.enabled") is True and get("combat.fleet_mode") in COMBINED_FLEET_MODES:
        # When the combat module is off, the combined-fleet setting has no effect, so downgrade to a warning
        level = ERROR if get("combat.enabled") is True else WARNING
        issues.append(
            Issue(
                level,
                ("pvp.enabled", "combat.fleet_mode"),
                t("PvP cannot be enabled while the sortie fleet is a combined fleet"),
            )
        )

    # LBAS: an enabled group should have target nodes, and a group with target nodes should be enabled
    groups = get("combat.lbas_groups")
    if isinstance(groups, list):
        active = {str(g) for g in groups}
        for n in (1, 2, 3):
            key = f"combat.lbas_group_{n}_nodes"
            nodes = get(key)
            if not isinstance(nodes, list):
                continue
            if str(n) in active and len(nodes) == 0:
                issues.append(
                    Issue(
                        WARNING,
                        ("combat.lbas_groups", key),
                        t("LBAS group {n} is enabled but has no target nodes", n=n),
                    )
                )
            elif str(n) not in active and len(nodes) > 0:
                issues.append(
                    Issue(
                        WARNING,
                        ("combat.lbas_groups", key),
                        t("LBAS group {n} has target nodes but is not enabled", n=n),
                    )
                )

    # Asking for both "retreat" and "push on" at the same node is contradictory
    retreat, push = get("combat.retreat_points"), get("combat.push_nodes")
    if isinstance(retreat, list) and isinstance(push, list):
        both = sorted({str(x) for x in retreat} & {str(x) for x in push})
        if both:
            issues.append(
                Issue(
                    WARNING,
                    ("combat.retreat_points", "combat.push_nodes"),
                    t(
                        "Node(s) {nodes} appear in both retreat and push-on lists",
                        nodes=t(", ").join(both),
                    ),
                )
            )

    # Heuristic reminder (not stated in Ch5, warning only): when the repair threshold is higher than the retreat threshold,
    # ships that just returned to port after retreating have a damage level below the repair threshold and will not be repaired before the next sortie
    retreat_limit, repair_limit = (
        get("combat.retreat_limit"),
        get("combat.repair_limit"),
    )
    if (
        isinstance(retreat_limit, int)
        and isinstance(repair_limit, int)
        and not isinstance(retreat_limit, bool)
        and not isinstance(repair_limit, bool)
        and repair_limit > retreat_limit
    ):
        issues.append(
            Issue(
                WARNING,
                ("combat.retreat_limit", "combat.repair_limit"),
                t(
                    "Repair damage level is higher than the retreat level; retreated ships may not be repaired"
                ),
            )
        )

    return issues


def validate_all(values: Mapping[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for key, value in values.items():
        issues.extend(validate_field(key, value))
    issues.extend(validate_cross(values))
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level == ERROR for i in issues)


# When combat.override is false kcauto uses the default sortie settings in data/combat;
# only the keys below still use the config file's values, all other combat.* keys are ignored by the system.
OVERRIDE_KEY = "combat.override"
OVERRIDE_EXEMPT = frozenset(
    {"combat.enabled", "combat.fleet_presets", "combat.sortie_map", OVERRIDE_KEY}
)


def ignored_by_override(key: str, override: Any) -> bool:
    """Whether this setting is currently ignored by the system (it can be changed but has no effect)."""
    return (
        key.startswith("combat.")
        and key not in OVERRIDE_EXEMPT
        and override is not True
    )
