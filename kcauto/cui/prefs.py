"""The CUI preference file (data layer, no UI dependency).

Same mechanism as ``config_cui.json``: **defaults in the code ← template file ← user file**, each layer
overriding the previous one.

* user file:      ``configs/cui_prefs.json`` (written by the CUI; it holds only what the user changed)
* template file:  ``template/configs/cui_prefs.json`` (read only; used for everything the user file lacks,
  so it is the whole preference set while ``configs/cui_prefs.json`` does not exist)

Keys: ``lang`` (editor language code), ``debug`` (bool, start kcauto with ``--debug-output``) and ``keys``
(shortcut overrides, see keymap.py). The ``keys`` object is merged entry by entry, every other value is
replaced as a whole. Unknown keys are kept when the user file is written.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PREF_FILE = Path("configs") / "cui_prefs.json"
TEMPLATE_FILE = Path("template") / "configs" / "cui_prefs.json"
MERGED_SECTIONS = ("keys",)


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_checked(path: Path) -> tuple[dict[str, Any], str]:
    """(content, problem). A missing file is not a problem; an unreadable or non-object file is."""
    if not path.is_file():
        return {}, ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, f"{path}: cannot read preferences ({exc}); ignored"
    if not isinstance(data, dict):
        return {}, f"{path}: must contain a JSON object; ignored"
    return data, ""


def load(root: Path | str = ".") -> tuple[dict[str, Any], list[str]]:
    """The effective preferences (template ← user file) and the problems found while reading them."""
    problems: list[str] = []
    merged: dict[str, Any] = {}
    for rel in (TEMPLATE_FILE, PREF_FILE):
        layer, problem = _read_checked(Path(root) / rel)
        if problem:
            problems.append(problem)
        for name, value in layer.items():
            if (
                name in MERGED_SECTIONS
                and isinstance(value, dict)
                and isinstance(merged.get(name), dict)
            ):
                merged[name] = {**merged[name], **value}
            else:
                merged[name] = value
    return merged, problems


def load_value(name: str, default: Any = None, root: Path | str = ".") -> Any:
    return load(root)[0].get(name, default)


def load_bool(name: str, default: bool = False, root: Path | str = ".") -> bool:
    value = load_value(name, default, root)
    return value if isinstance(value, bool) else default


def save_value(name: str, value: Any, root: Path | str = ".") -> bool:
    """Write one value into the user file (created when missing); its other entries are kept and the
    template is never touched."""
    path = Path(root) / PREF_FILE
    data = _read(path)
    data[name] = value
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return True
    except OSError:
        return False
