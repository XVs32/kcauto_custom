"""User-customisable shortcut keys (data layer, no UI dependency).

Only *command* keys can be changed: the dashboard commands, the module jump keys and a handful
of editor commands. Navigation and editing keys (arrows, Enter, Esc, Tab, PgUp/PgDn, Home/End,
Space inside the editor, + / - nudging) and everything inside dialogs are fixed.

Overrides live in ``configs/tui_prefs.json`` under ``"keys"`` (only the entries you changed)::

    {"lang": "en", "keys": {"pause": "p", "module.combat": "1"}}

* Keys are a single lowercase letter or digit, one of ``/ [ ] , . ;``, ``space``, ``f1``..``f12`` or
  ``shift+enter`` (the default of ``toggle``) or ``ctrl+enter``. A bare Shift key cannot be detected in a
  terminal, so ``"shift"`` is read as ``shift+enter``. Many terminals cannot tell Shift+Enter / Ctrl+Enter
  from Enter; if it does nothing in yours, give ``toggle`` a plain key, e.g. ``{"keys": {"toggle": "x"}}``.
* There is no save or apply key: the config is saved when it is applied (Enter or a click on the log
  panel, then confirm) or when you choose "save and quit". Old ``save`` / ``apply`` entries are ignored.
* The same key cannot be used twice inside one screen (dashboard / editor). Offending overrides
  are dropped and every problem is reported (see :attr:`Keymap.problems`); defaults are used instead.
* Keys are read **once at start-up**; changes take effect the next time the CUI is started.

Run ``python kcauto/kcauto_cui.py --show-keys`` to list every action id with its current and default key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

PREF_FILE = Path("configs") / "tui_prefs.json"
SECTION = "keys"

DASHBOARD = "dashboard"
EDITOR = "editor"
BOTH = (DASHBOARD, EDITOR)


@dataclass(frozen=True)
class Action:
    id: str
    default: str
    scopes: tuple[str, ...]
    label: str


# (module, default key, scopes) in dashboard order; "other" (unknown keys) only exists in the editor
_MODULE_KEYS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("combat", "c", BOTH),
    ("expedition", "e", BOTH),
    ("pvp", "p", BOTH),
    ("quest", "u", BOTH),
    ("scheduler", "s", BOTH),
    ("factory", "f", BOTH),
    ("passive_repair", "r", BOTH),
    ("ship_switcher", "h", BOTH),
    ("event_reset", "v", BOTH),
    ("general", "g", BOTH),
    ("other", "o", (EDITOR,)),
)

ACTIONS: tuple[Action, ...] = (
    Action("quit", "q", (DASHBOARD,), "Quit"),
    Action("pause", "space", (DASHBOARD,), "Pause / resume kcauto"),
    Action("log", "l", (DASHBOARD,), "Focus the log (full screen when hidden)"),
    Action("language", "t", (DASHBOARD,), "Choose the editor language"),
    Action(
        "toggle",
        "shift+enter",
        (DASHBOARD,),
        "Toggle the focused module's enabled switch",
    ),
    Action(
        "debug",
        "d",
        (DASHBOARD,),
        "Toggle debug output (adds --debug-output on the next start)",
    ),
    Action("editor.reset_default", "d", (EDITOR,), "Reset the field to its default"),
    Action("editor.undo", "z", (EDITOR,), "Revert the field to the saved value"),
    Action("editor.search", "/", (EDITOR,), "Search all fields"),
    Action("editor.module_prev", "[", (EDITOR,), "Previous module"),
    Action("editor.module_next", "]", (EDITOR,), "Next module"),
    *(
        Action(f"module.{m}", k, scopes, f"Jump to {m}")
        for m, k, scopes in _MODULE_KEYS
    ),
)
BY_ID = {a.id: a for a in ACTIONS}
# Actions that used to exist; their overrides are ignored without a warning.
RETIRED = frozenset({"save", "apply"})

# Never assignable: navigation / editing keys and the modifier-free names Textual uses for them.
RESERVED = frozenset(
    {
        "up",
        "down",
        "left",
        "right",
        "enter",
        "return",
        "escape",
        "esc",
        "tab",
        "shift+tab",
        "pageup",
        "pagedown",
        "home",
        "end",
        "backspace",
        "delete",
        "insert",
        "+",
        "-",
        "=",
        "plus",
        "minus",
    }
)
# Reserved only on one screen: Space is the editor's "Enter-like" key.
SCOPE_RESERVED: dict[str, frozenset[str]] = {EDITOR: frozenset({"space"})}

PUNCTUATION = "/[],.;"
_ALIASES = {
    "spacebar": "space",
    "space bar": "space",
    "slash": "/",
    "left_square_bracket": "[",
    "right_square_bracket": "]",
    "comma": ",",
    "full_stop": ".",
    "period": ".",
    "semicolon": ";",
}
# Textual names for the punctuation we allow (a Binding takes "name,char" so either form matches).
_BINDING_NAMES = {
    "/": "slash",
    "[": "left_square_bracket",
    "]": "right_square_bracket",
    ",": "comma",
    ".": "full_stop",
    ";": "semicolon",
}
_FUNCTION_KEYS = frozenset(f"f{n}" for n in range(1, 13))
CTRL_ENTER = "ctrl+enter"
SHIFT_ENTER = "shift+enter"
MODIFIED_ENTER = frozenset({CTRL_ENTER, SHIFT_ENTER})
_ALIASES.update(
    {"ctrl+return": CTRL_ENTER, "shift+return": SHIFT_ENTER, "shift": SHIFT_ENTER}
)
# Terminals that cannot send a distinct Ctrl+Enter often send Ctrl+J (a line feed) instead.
_BINDING_EXTRA = {CTRL_ENTER: "ctrl+j"}


def normalize(raw: Any) -> tuple[Optional[str], str]:
    """(key, problem). ``key`` is None when the text is not an acceptable key."""
    if not isinstance(raw, str):
        return None, "must be a string"
    text = raw.strip()
    if not text:
        return None, "is empty"
    low = text.lower()
    if low in RESERVED:
        return None, f"{text!r} is a navigation key and cannot be reassigned"
    aliased = _ALIASES.get(low, low)
    if aliased != low:  # "slash" → "/", "spacebar" → "space", ...
        low = text = aliased
    if low == "space" or low in MODIFIED_ENTER or low in _FUNCTION_KEYS:
        return low, ""
    if len(text) == 1:
        if text.isascii() and text.isalpha() and text.isupper():
            return None, f"{text!r}: use the lowercase letter (Shift is not supported)"
        if text.isascii() and text.isalnum():
            return text, ""
        if text in PUNCTUATION:
            return text, ""
        return (
            None,
            f"{text!r} is not allowed (letters, digits, / [ ] , . ; space, f1-f12, shift+enter, ctrl+enter)",
        )
    return (
        None,
        f"{text!r} is not a valid key (letters, digits, / [ ] , . ; space, f1-f12, shift+enter, ctrl+enter)",
    )


class Keymap:
    """The resolved key for every action, plus any problems found in the overrides."""

    def __init__(self, overrides: Optional[Mapping[str, Any]] = None) -> None:
        self.problems: list[str] = []
        self.overrides: dict[str, str] = {}
        self._assigned = {a.id: a.default for a in ACTIONS}
        self._resolve(overrides or {})

    # -- queries ------------------------------------------------------- #
    def key(self, action: str) -> str:
        return self._assigned[action]

    def display(self, action: str) -> str:
        return self._assigned[action]

    def binding_key(self, action: str) -> str:
        """The key as a Textual ``Binding`` key string."""
        key = self._assigned[action]
        name = _BINDING_NAMES.get(key) or _BINDING_EXTRA.get(key)
        return f"{name},{key}" if name else key

    def module_key(self, module: str) -> str:
        return self._assigned[f"module.{module}"]

    def in_scope(self, scope: str) -> list[Action]:
        return [a for a in ACTIONS if scope in a.scopes]

    # -- resolving ----------------------------------------------------- #
    def _resolve(self, overrides: Mapping[str, Any]) -> None:
        wanted: dict[str, str] = {}
        for action_id, raw in overrides.items():
            action = BY_ID.get(action_id)
            if action is None and action_id in RETIRED:
                continue
            if action is None:
                self.problems.append(f"{action_id}: unknown action (ignored)")
                continue
            key, problem = normalize(raw)
            if key is None:
                self.problems.append(
                    f"{action_id}: {problem}; using the default {action.default!r}"
                )
                continue
            bad_scope = next(
                (s for s in action.scopes if key in SCOPE_RESERVED.get(s, ())), None
            )
            if bad_scope is not None:
                self.problems.append(
                    f"{action_id}: {key!r} is reserved in the {bad_scope}; "
                    f"using the default {action.default!r}"
                )
                continue
            wanted[action_id] = key
        self._assigned.update(wanted)
        # A key may be used once per screen. Drop the overrides that collide and re-check,
        # because reverting one can free (or take) another action's key.
        while True:
            collided = False
            for scope in BOTH:
                users: dict[str, list[str]] = {}
                for action in self.in_scope(scope):
                    users.setdefault(self._assigned[action.id], []).append(action.id)
                for key, ids in users.items():
                    mine = [i for i in ids if i in wanted]
                    if len(ids) > 1 and mine:
                        self.problems.append(
                            f"{', '.join(ids)}: key {key!r} is used more than once on the {scope}; "
                            f"reverted to the default for {', '.join(mine)}"
                        )
                        for i in mine:
                            del wanted[i]
                            self._assigned[i] = BY_ID[i].default
                        collided = True
            if not collided:
                break
        self.overrides = {i: k for i, k in wanted.items() if k != BY_ID[i].default}

    def describe(self) -> str:
        lines = [f"{'action':<24}{'key':<13}{'default':<13}description"]
        for a in ACTIONS:
            mark = "*" if self._assigned[a.id] != a.default else " "
            lines.append(
                f"{a.id:<24}{self._assigned[a.id]:<12}{mark}{a.default:<13}{a.label}"
            )
        lines.append("")
        lines.append(
            "* = changed.  Edit configs/tui_prefs.json:  "
            '{"keys": {"pause": "p", "module.combat": "1"}}'
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------- #
# The active keymap. Load it ONCE, before anything that builds bindings is imported.
# ---------------------------------------------------------------------- #
_active = Keymap()


def active() -> Keymap:
    return _active


def reset() -> Keymap:
    """Back to the defaults (used by tests)."""
    global _active
    _active = Keymap()
    return _active


def load_overrides(root: Path | str = ".") -> tuple[dict[str, Any], list[str]]:
    path = Path(root) / PREF_FILE
    if not path.is_file():
        return {}, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, [f"{path}: cannot read key settings ({exc}); using defaults"]
    section = data.get(SECTION) if isinstance(data, dict) else None
    if section is None:
        return {}, []
    if not isinstance(section, dict):
        return {}, [f'{path}: "{SECTION}" must be an object; using defaults']
    return dict(section), []


def init(root: Path | str = ".") -> Keymap:
    """Read the overrides from ``configs/tui_prefs.json`` and make them the active keymap."""
    global _active
    overrides, problems = load_overrides(root)
    _active = Keymap(overrides)
    _active.problems[:0] = problems
    return _active
