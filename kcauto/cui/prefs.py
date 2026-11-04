"""Small helpers for the preference file ``configs/tui_prefs.json`` (data layer, no UI dependency).

Other keys in the file (``lang``, ``keys``) are always preserved when one value is written.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PREF_FILE = Path("configs") / "tui_prefs.json"


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_bool(name: str, default: bool = False, root: Path | str = ".") -> bool:
    value = _read(Path(root) / PREF_FILE).get(name, default)
    return value if isinstance(value, bool) else default


def save_value(name: str, value: Any, root: Path | str = ".") -> bool:
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
