"""ConfigStore: the CUI's config data layer (not coupled to the UI or the kcauto process).

Responsibilities
  * Loading: schema defaults ← template file ← user config file, each layer overriding the previous.
  * Unknown keys are always kept and written back as-is, so a newer kcauto adding a field is not swallowed by the CUI.
  * Track modifications (dirty / changed_keys); a single field or everything can be reverted.
  * Validation: single field + cross-field, reported as ``Issue``.
  * Saving: back up first, then "write temp file → fsync → os.replace", so the bot never reads half-written JSON.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from . import akashi
from .schema import (
    SCHEMA,
    Issue,
    defaults,
    has_errors,
    validate_all,
    validate_cross,
    validate_field,
)

Listener = Callable[[Optional[str]], None]


class ConfigLoadError(Exception):
    """The config or template cannot be read (for reasons other than not existing, e.g. corrupt JSON)."""


class ConfigValidationError(Exception):
    """An error-level issue was found when saving."""

    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__("Config has errors:\n" + "\n".join(str(i) for i in issues))


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ConfigLoadError(f"{path} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise ConfigLoadError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigLoadError(f"The top level of {path} must be a JSON object")
    return data


PASSIVE_REPAIR_KEY = "passive_repair.enabled"


class ConfigStore:
    def __init__(
        self,
        path: os.PathLike | str,
        template_path: os.PathLike | str | None = None,
    ) -> None:
        self.path = Path(path)
        self.template_path = Path(template_path) if template_path else None
        self.is_new_file = False
        self._values: dict[str, Any] = {}
        self._saved: dict[str, Any] = {}
        self._unknown_order: list[str] = []
        self._listeners: list[Listener] = []
        self.load()

    # ------------------------------------------------------------------ #
    # loading
    # ------------------------------------------------------------------ #
    def load(self) -> None:
        merged = defaults()
        if self.template_path is not None and self.template_path.is_file():
            merged.update(_read_json_object(self.template_path))

        self.is_new_file = not self.path.is_file()
        if not self.is_new_file:
            merged.update(_read_json_object(self.path))

        self._unknown_order = [k for k in merged if k not in SCHEMA]
        self._values = merged
        self._saved = copy.deepcopy(merged)
        self.forced_notes: list[
            str
        ] = []  # settings that were forced to change (the UI shows a notification after reading them)
        self._enforce()
        self._notify(None)

    # ------------------------------------------------------------------ #
    # read / write
    # ------------------------------------------------------------------ #
    def get(self, key: str) -> Any:
        """Return a copy of the value; changing it outside does not affect the internal state."""
        return copy.deepcopy(self._values[key])

    def __contains__(self, key: str) -> bool:
        return key in self._values

    def keys(self) -> list[str]:
        return list(self._ordered_keys())

    def as_dict(self) -> dict[str, Any]:
        return {k: copy.deepcopy(self._values[k]) for k in self._ordered_keys()}

    def set(self, key: str, value: Any) -> list[Issue]:
        """Set a field and return the issues related to it (including cross-field ones).

        Invalid values are still kept (the editor needs to show what the user is typing); whether saving / applying is allowed is decided by ``save``.
        """
        value = copy.deepcopy(value)
        if key not in SCHEMA and key not in self._values:
            self._unknown_order.append(key)
        was = self._values.get(key)
        self._values[key] = value
        if key == akashi.ENABLED_KEY:  # Akashi repair switch: the rules follow it
            self._values[akashi.SLOTS_KEY] = akashi.slots_for(
                value is True, self._values.get(akashi.SLOTS_KEY)
            )
            self._notify(akashi.SLOTS_KEY)
        self._enforce()
        self._notify(key)
        if key == akashi.COMBAT_ENABLED_KEY and was is True and value is False:
            self._combat_disabled()
        return self.issues_for(key)

    def _combat_disabled(self) -> None:
        """Combat was just switched off: turn Akashi repair and passive repair on.

        Only a user toggle triggers this (not load / revert), and there is no reverse rule
        for passive repair when combat is enabled. Notifies only if something changed.
        """
        changed = False
        for key in (akashi.ENABLED_KEY, PASSIVE_REPAIR_KEY):
            if self._values.get(key) is not True:
                self.set(key, True)
                changed = True
        if changed:
            self.forced_notes.append("combat_off")

    def reset_key(self, key: str) -> None:
        """Reset to the schema default (unknown fields have no default and are ignored)."""
        field = SCHEMA.get(key)
        if field is not None:
            self.set(key, field.make_default())

    def revert_key(self, key: str) -> None:
        """Revert to the value at the last save (or load)."""
        if key in self._saved:
            self._values[key] = copy.deepcopy(self._saved[key])
            if key == akashi.ENABLED_KEY and akashi.SLOTS_KEY in self._saved:
                self._values[akashi.SLOTS_KEY] = copy.deepcopy(
                    self._saved[akashi.SLOTS_KEY]
                )
                self._notify(akashi.SLOTS_KEY)
            self._enforce()
            self._notify(key)

    def revert_all(self) -> None:
        self._values = copy.deepcopy(self._saved)
        self._enforce()
        self._notify(None)

    def _enforce(self) -> None:
        """Force Akashi repair off when combat is enabled (the rules are cleared too). Notifies only if something changed."""
        if (
            akashi.forced_off(self._values)
            and self._values.get(akashi.ENABLED_KEY) is True
        ):
            self._values[akashi.ENABLED_KEY] = False
            self._values[akashi.SLOTS_KEY] = {}
            self.forced_notes.append("akashi")
            self._notify(akashi.SLOTS_KEY)
            self._notify(akashi.ENABLED_KEY)

    def pop_forced(self) -> list[str]:
        notes, self.forced_notes = self.forced_notes, []
        return notes

    # ------------------------------------------------------------------ #
    # modification state
    # ------------------------------------------------------------------ #
    def changed_keys(self) -> list[str]:
        return [
            k
            for k in self._ordered_keys()
            if k not in self._saved or self._values[k] != self._saved[k]
        ]

    @property
    def is_dirty(self) -> bool:
        return self.is_new_file or bool(self.changed_keys())

    def is_changed(self, key: str) -> bool:
        return key not in self._saved or self._values.get(key) != self._saved[key]

    # ------------------------------------------------------------------ #
    # validation
    # ------------------------------------------------------------------ #
    def issues(self) -> list[Issue]:
        return validate_all(self._values)

    def issues_for(self, key: str) -> list[Issue]:
        found = validate_field(key, self._values.get(key))
        found += [i for i in validate_cross(self._values) if key in i.keys]
        return found

    def has_errors(self) -> bool:
        return has_errors(self.issues())

    # ------------------------------------------------------------------ #
    # saving
    # ------------------------------------------------------------------ #
    def save(self, *, force: bool = False, backup: bool = True) -> Path:
        """Write the config file atomically. Refuses when there are error-level issues, unless ``force=True``."""
        problems = [i for i in self.issues() if i.level == "error"]
        if problems and not force:
            raise ConfigValidationError(problems)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        if backup and self.path.is_file():
            self._write_backup()

        payload = json.dumps(self.as_dict(), indent=4, ensure_ascii=False) + "\n"
        fd, tmp_name = tempfile.mkstemp(
            prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, self.path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

        self._saved = copy.deepcopy(self._values)
        self.is_new_file = False
        self._notify(None)
        return self.path

    @property
    def backup_path(self) -> Path:
        return self.path.with_name(self.path.name + ".bak")

    def _write_backup(self) -> None:
        data = self.path.read_bytes()
        self.backup_path.write_bytes(data)

    # ------------------------------------------------------------------ #
    # change notification (for UI subscribers)
    # ------------------------------------------------------------------ #
    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def unsubscribe(self, listener: Listener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify(self, key: Optional[str]) -> None:
        for listener in list(self._listeners):
            listener(key)

    # ------------------------------------------------------------------ #
    def _ordered_keys(self) -> Iterable[str]:
        """Schema order first; unknown fields follow in their original order of appearance."""
        for key in SCHEMA:
            if key in self._values:
                yield key
        for key in self._unknown_order:
            if key in self._values:
                yield key
