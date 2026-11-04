"""Multi-language support (data layer, no UI dependency).

* Language files live in ``cui/locales/<code>.json``. **Dropping a file in is enough for it to be detected**; to add a language just add one file::

      {
        "_name": "日本語",                       # name shown in the language menu
        "fields": {"combat.enabled": {"label": "...", "help": "..."}},   # label and help of config fields
        "messages": {"English source text": "translation"}              # all other UI text, keyed by the English source
      }

* English is the default and the fallback for anything missing: the code writes English directly, and ``t("text")`` returns it unchanged when no translation is found. So a language file may translate only part of the UI (for example, not the dashboard text).
* Sentences with variables use ``t("{n} selected", n=3)``; keep the same ``{n}`` in the translation file.
* Game abbreviations (DD, CV, ...), config keys, and most dashboard text stay English and do not go through here.

Language priority: ``--lang`` > environment variable ``KCAUTO_LANG`` > preference file (``configs/cui_prefs.json``, defaults from ``template/configs/cui_prefs.json``) > en.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from . import prefs

DEFAULT = "en"
LOCALE_DIR = Path(__file__).resolve().parent / "locales"
PREF_FILE = prefs.PREF_FILE
ENV_VAR = "KCAUTO_LANG"

_ALIASES = {
    "zh": "zh_TW",
    "zh_tw": "zh_TW",
    "zh-tw": "zh_TW",
    "zh_hant": "zh_TW",
    "tw": "zh_TW",
    "ja": "ja",
    "ja_jp": "ja",
    "ja-jp": "ja",
    "jp": "ja",
    "en": "en",
    "en_us": "en",
    "en-us": "en",
    "en_gb": "en",
}

_cache: dict[str, dict[str, Any]] = {}
_current = DEFAULT


# ---------------------------------------------------------------------- #
def _load(code: str) -> dict[str, Any]:
    if code not in _cache:
        data: dict[str, Any] = {}
        path = LOCALE_DIR / f"{code}.json"
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, ValueError):
            pass
        _cache[code] = data
    return _cache[code]


def available() -> list[tuple[str, str]]:
    """[(code, display name)], English always first, the rest sorted by code."""
    found = {DEFAULT: "English"}
    if LOCALE_DIR.is_dir():
        for path in sorted(LOCALE_DIR.glob("*.json")):
            name = _load(path.stem).get("_name")
            found[path.stem] = name if isinstance(name, str) and name else path.stem
    rest = sorted(c for c in found if c != DEFAULT)
    return [(c, found[c]) for c in [DEFAULT, *rest]]


def normalize(code: Optional[str]) -> Optional[str]:
    """Map spellings such as zh-TW or ja_JP to a language file that actually exists; None if not recognised."""
    if not code or not isinstance(code, str):
        return None
    raw = code.strip().split(".")[0]
    known = {c for c, _ in available()}
    for candidate in (raw, _ALIASES.get(raw.lower())):
        if candidate in known:
            return candidate
    low = {c.lower(): c for c in known}
    if raw.lower() in low:
        return low[raw.lower()]
    alias = _ALIASES.get(raw.lower())
    return alias if alias in known else None


def language() -> str:
    return _current


def set_language(code: Optional[str]) -> bool:
    """Switch language. If the code is not recognised, keep the current language and return False."""
    global _current
    norm = normalize(code)
    if norm is None:
        return False
    _current = norm
    return True


# ---------------------------------------------------------------------- #
def t(text: str, **fmt: Any) -> str:
    """Translate UI text. Falls back to the English source when no translation exists; applies ``str.format`` when ``fmt`` is given."""
    out = text
    if _current != DEFAULT:
        messages = _load(_current).get("messages")
        if isinstance(messages, dict):
            hit = messages.get(text)
            if isinstance(hit, str) and hit:
                out = hit
    if fmt:
        try:
            return out.format(**fmt)
        except (KeyError, IndexError, ValueError):
            try:
                return text.format(
                    **fmt
                )  # fall back to English when the translation file has a wrong placeholder
            except (KeyError, IndexError, ValueError):
                return text
    return out


def field_text(key: str, part: str, default: str) -> str:
    """Label (part="label") or help text (part="help") of a config field."""
    if _current != DEFAULT:
        fields = _load(_current).get("fields")
        if isinstance(fields, dict):
            entry = fields.get(key)
            if isinstance(entry, dict):
                hit = entry.get(part)
                if isinstance(hit, str) and hit:
                    return hit
    return default


# ---------------------------------------------------------------------- #
# Preference file (see prefs.py; the language chosen in the menu is saved in it)
# ---------------------------------------------------------------------- #
def load_pref(root: Path | str = ".") -> Optional[str]:
    """The saved language: user file, else the template file (see prefs.py)."""
    return normalize(prefs.load_value("lang", None, root))


def save_pref(code: str, root: Path | str = ".") -> bool:
    return prefs.save_value("lang", code, root)


def init(cli_lang: Optional[str] = None, root: Path | str = ".") -> str:
    """Decide the language at startup: --lang > KCAUTO_LANG > preference file > en. Returns the code finally used."""
    for candidate in (cli_lang, os.environ.get(ENV_VAR), load_pref(root)):
        if candidate and set_language(candidate):
            return _current
    set_language(DEFAULT)
    return _current
