# kcauto_custom CUI (rewrite)

A btop-style dashboard and full-screen config editor for kcauto_custom, built on
[Textual](https://textual.textualize.io/). It edits `configs/config_cui.json`, starts and
controls the kcauto process, and shows its log.

## Install and run

```
pip install "textual>=0.86" psutil     # Python 3.11+
python kcauto/kcauto_cui.py            # run from the project root; reads configs/config_cui.json
python kcauto/kcauto_cui.py --config PATH --template PATH --lang ja --autostart --debug-output
```

Run it from the project root: the CUI starts kcauto from the current working directory
(`./bin/kcauto_custom/kcauto_custom[.exe]`, otherwise `python kcauto`) with
`--cli --cfg <config name>`.

| Option | Meaning |
|---|---|
| `--config PATH` | config file (default `configs/config_cui.json`) |
| `--template PATH` | template file used for defaults |
| `--lang CODE` | editor language: `en` (default), `zh_TW`, `ja` |
| `--autostart` | start kcauto right after opening (off by default) |
| `--debug-output` | start in debug mode: kcauto is started with `--debug-output` (see below) |

## Tests

```
python -m unittest discover -s tests -t . -v
```

- The pure-Python parts (schema, store, summaries, model logic) need no Textual.
- Without Textual, `tests/textual_stub.py` lets the dialog / widget *logic* run; the real UI
  tests (`tests/test_app.py`, `tests/test_editor_ui.py`) need Textual and are skipped otherwise.
- Set `KCAUTO_TEMPLATE=<template.json>`, `KCAUTO_QUESTS=<quests.json>` or
  `KCAUTO_NORO6=<configs/noro6/noro6>` to check the schema / quest catalogue / noro6 reader
  against your real files.

## Dashboard

| Key | Action |
|---|---|
| arrow keys | move between boxes; walking past the edge toward the log enters the log |
| `c e p u s f r h v g` | jump straight to that module's box |
| Shift+Enter / click ON·OFF at the bottom right | toggle the box's `enabled` (see the note on terminals below) |
| `d` | toggle debug mode (`--debug-output`, applies on the next start) |
| Space | pause / resume kcauto (works anywhere on the dashboard) |
| Enter / double-click | open the editor on that module |
| `l` | focus the log; when the log is hidden by the layout, show it full screen (works, but is not shown in the hint bar) |
| Esc | leave the log / full-screen log |
| `t` | choose the editor language |
| `q` | quit; asks when there are unsaved changes (**save and quit** / discard / cancel) or kcauto is running |

On the log:

| Key | Action |
|---|---|
| ↑ ↓ / PgUp PgDn | scroll |
| ← | back to the boxes (with the log below, ↑ at the very top also goes back) |
| Enter, or a mouse click on the log | if kcauto is waiting at `Press Enter to continue`, send Enter; otherwise **apply**: ask for confirmation, then save the config and (re)start kcauto |

**Apply asks first.** The dialog says how many settings will be saved and whether kcauto will be started or restarted;
`y` / Enter / a click on "Apply" goes ahead, `n` / Esc / a click on "Cancel" does nothing. It is not offered while the config has errors.
A click applies only when the log already had the focus (focus it with `l` or the arrow keys first): the click that merely
focuses the log does nothing.

**There is no save key.** The config file is written when you apply, or with "save and quit" when leaving.

**Shift+Enter** needs a terminal that reports it (kitty-protocol terminals, ...); many terminals send a plain Enter instead.
If it does nothing in yours, give `toggle` a plain key in `configs/tui_prefs.json`, e.g. `{"keys": {"toggle": "x"}}`
(a bare `"shift"` is read as `shift+enter`, because a terminal cannot report the Shift key alone; `ctrl+enter` is accepted too).

The dashboard text is English only. The editor (labels, help, dialogs, messages) follows the
selected language.

### Responsive layout

| Condition | Layout |
|---|---|
| enough width for at least one card column plus a 40-column log | log on the right; cards use the **fewest columns (1-4) that fit the screen height**, and all spare width goes to the log |
| not enough width, enough height | log below the dashboard; cards use 1-4 columns by width |
| neither | log hidden, cards fill the screen (`l` shows the log full screen) |

The numbers live in `kcauto/cui/layout.py`; `kcauto/cui/theme.tcss` must match (`tests/test_layout.py` checks it).

### kcauto process control

Kept from the old CUI: the start command, `--cli --cfg <name>`, the ANSI colour convention
(91 error / 92 status / 93 warning / 94 log), pausing with suspend / resume, detection of
`Press Enter to continue`, and "reload config = end the process and start it again".

Different (all fixes):

- **Never starts automatically** (apply with Enter on the log, or use `--autostart`).
- Ending kcauto also ends its **child processes**, and leaving the CUI always cleans kcauto up.
- Child processes get `PYTHONUNBUFFERED=1` and `PYTHONIOENCODING=utf-8`, so the log is not delayed
  and does not turn into garbage on Windows.
- The Python fallback uses `sys.executable`, not `python` / `python3` from PATH.
- Compound ANSI parameters such as `91;1` are parsed correctly.
- The log keeps the latest 3000 lines, even while hidden.

**Debug mode.** `d` toggles debug mode, which appends `--debug-output` to the kcauto command line
(`... --cli --cfg <name> --debug-output`). It applies from the **next** start: if kcauto is running,
apply (Enter on the log) to restart it. The status bar shows `DEBUG` while the mode is on, and the choice is
remembered in `configs/tui_prefs.json` (`"debug": true`). `--debug-output` on the CUI command line
turns it on for that session as well.

There is no separate "stop" key: quit the CUI (`q`) to end kcauto, or apply (Enter on the log) to restart it.

The status bar shows: run state, uptime, CPU sparkline and percentage, memory, and a hint when
kcauto is waiting for Enter.

## Editor

Open it with Enter or a double-click on a box. All edits are applied to the in-memory config
immediately and shown on the dashboard; they are written to the file when you apply on the dashboard (Enter or a click on the log, then confirm) or choose "save and quit". kcauto's log keeps accumulating while you edit.

| Key | Action |
|---|---|
| ↑ ↓ / PgUp PgDn / Home End | move between fields |
| ← | back to the module list (below 72 columns ← → switch modules) |
| `c e p u s f r h v g o` | jump to that module (`o` = unknown keys) |
| `[` `]` | previous / next module |
| Enter / click | edit (opens the control for the field's type) |
| Space | toggle a switch, cycle an enum; same as Enter for other types |
| `+` `-` | nudge an integer, cycle an enum |
| `d` | reset to the default |
| `z` | revert to the last saved value |
| `/` | search all fields (key, label, help; the current language and English) |
| Esc | leave the editor |

The first row of the module list is `..`: select it (↑ from the first module, then Enter or a
click) to go back to the dashboard, exactly like Esc.

Field rows: `✖` error, `⚠` warning, `!` high risk, `*` modified. The bottom panel shows the key,
help, type, default, current value and issues.

### Two-level operation (all fields)

- **Level 1 (list):** ↑ ↓ only move between fields; ← goes to the module list. **Enter** enters a field.
- **Switches, enums and integers with a few levels** enter in place: the whole row is highlighted and
  `‹ ›` appear around the value. ← → change the value (`+` `-` also work, Space = next value);
  Enter confirms, Esc restores the value from before entering.
  **Switches and enums cycle**: either arrow flips a switch, and an enum wraps around at the ends.
  Small-range integers stop at their ends.
- **Everything else** opens a dialog (Enter = OK, Esc = cancel; inside an input box Enter adds / confirms
  the item, and Enter on an empty box = OK).
- While editing a row, ↑ ↓, module shortcuts and `d z w /` are disabled so you cannot leave by accident.

**Mouse:** the first click only selects a row; clicking an already selected row enters editing, where
`‹ ›` become clickable; clicking another row or pressing Enter confirms. Non-adjustable fields open
their dialog with one click.

### Controls by field type

**Principle: numbers are never typed.** Small level-like integers use ← →; other numbers use
digit-by-digit wheels (like a phone alarm clock).

| Field | Control |
|---|---|
| bool, enum (including `null`) | in-place editing; `null` is shown as `disable` |
| integers with few levels (damage levels 0-4, difficulty 1-4, ...) | in-place editing, ← → |
| other integers (ports, resource targets, time, offset, ...) | **digit wheel**: ← → digit, ↑ previous value, ↓ next value, Enter confirm; out-of-range values snap into range; a ± wheel when negatives are allowed |
| `combat.sortie_map` | three wheels: world (auto / 1-7 / E), map number, **target node**. Nodes come from `configs/noro6/noro6` (fallback `template/configs/noro6/noro6`) and only nodes that really have a preset are offered (`B-2-2-A` → `2-2-A`); `—` = no node. `-bak` presets are skipped |
| `factory.build_recipe`, `factory.develop_recipe` | 2×2 wheels (top: fuel, steel; bottom: ammo, bauxite), two-level. Level 1: arrows choose a resource or the `[ OK ] [ Cancel ]` cells; level 2: adjust that resource's digits. The saved order is still `[fuel, ammo, steel, bauxite]`. A **Presets** list is read from `data/factory/construct_recipe_preset.json` / `develop_recipe_preset.json`; applying a preset sets the four resources and the matching secretary. The list sits left of the wheels when the terminal is at least 92 columns wide, otherwise above them (`p`, ← or ↑ moves into it) |
| `factory.build_secretary`, `factory.develop_secretary` | a list of ship types (DE, DD, CL, CLT, CA, CAV, CVL, FBB, BB, BBV, CV, SS, SSV, AV, LHA, CVB, AR, AS, CT, AO) plus **Production ID…**, which opens a digit wheel. Ship type codes stay in English in every language |
| `combat.fleet_presets`, `pvp.fleet_preset` | a single-value scrolling list: `disable`, `auto`, then 1-15. `fleet_presets` always writes exactly one element (`disable` = empty list); `null` / `0` show as `disable`. `expedition.fleet_preset` is an enum (disable, auto) |
| `combat.lbas_groups` | three tick boxes: 1 / 2 / 3 |
| string arrays | list editor: paste several items at once (comma / space separated); ↓ enters the list, Enter edits an item, Delete / `x` removes it |
| `combat.node_selects`, `node_formations`, `node_night_battles` | two-column tables |
| `scheduler.rules` | a dedicated dialog with exactly two rules: **stop kcauto at HH:MM** (`time:HHMM:stop:kcauto`) and **stop combat after N sorties** (`sorties_run:N:stop:combat`). Space = on/off, Enter = set value, `o` = OK. Other rules are removed when you press OK |
| `quest.quests` | checklist grouped by prefix (events first, newest first); a group header folds / unfolds it, Space ticks a quest. Only quests in `data/quests/quests.json` (fallback `template/data/quests/quests.json`) are listed; selected quests missing from the file go to an `other` group so they are never lost |
| `ship_switcher.enabled` ("Akashi repair") | one switch: on fills `ship_switcher.slots` with the fixed Akashi repair rules, off clears them. `ship_switcher.slots` itself is not shown. See *Linked settings* below |
| unknown keys holding objects / lists | **tree-table editor** (below); scalar unknown keys use a JSON editor |
| `combat.push_nodes` | adding a node asks for confirmation (y / n); removing does not |
| expeditions | the first row "All fleets 2/3/4" sets fleets 2, 3 and 4 at once (`auto`, `overnight`, a custom list, or clear); `d` / `z` reset / revert all three. Add presets in `EXPEDITION_PRESETS` in `editor/model.py` |

Lists and tables that have **OK / Cancel** buttons below them: press ↓ at the end of the list to move
to the buttons, ← → to switch button, Enter / Space to press, ↑ to go back to the list.

### Linked settings

- `combat.override` off → every `combat.*` setting except `enabled`, `fleet_presets` and `sortie_map`
  is shown in grey: it can still be changed, but kcauto ignores it (it uses the defaults in `data/combat`).
- **Akashi repair and combat are exclusive**: enabling combat turns Akashi repair off (and clears its
  rules), and Akashi repair cannot be turned on while combat is enabled. A file that has both on is
  corrected on load and shows as modified.
- **Turning combat off** (a real on → off toggle, including `d` reset) turns **Akashi repair** and
  **passive repair** on. Turning combat on does not touch passive repair. Loading and reverting
  never trigger this.

### Tree-table editor (`ship_switcher.slots` and unknown keys)

Settings without a fixed structure are edited as an expandable table, one node per row:

```
▾ 1                 object {3}
    ship            int    123
  ▾ rules           list   [2]
      [0]           str    "a"
      [1]           bool   on
▸ 2                 object {0}
```

| Key | Action |
|---|---|
| ↑ ↓ | move; the current path (e.g. `1.rules[0]`) is shown above |
| → / ← | expand / collapse; ← on a non-container goes to the parent |
| Enter / click | container = expand / collapse; bool = toggle; integer = digit wheel; string / decimal = input box |
| `a` | add (inside a container, or beside a plain value); objects ask for a key first, then the type; lists only ask for the type |
| `x` / Delete | delete the node |
| `r` | rename the key (order is kept; duplicate keys are refused) |
| `t` | change the type (content is kept when it converts cleanly, e.g. `"12"` → 12) |
| `j` | edit as raw JSON (syntax errors are shown live) |
| Ctrl+S or OK | apply; Esc cancels without touching the original |

You edit a working copy, and the top level must keep its type (an object cannot become a list).

### Narrow and short windows

| Window | Change |
|---|---|
| < 72 columns | the module list is hidden; a one-row "‹ previous [ current ] next ›" switcher is shown on top, centred on the current module (click the left / right third, or use `[` `]` and the module shortcuts) |
| < 50 columns | every field takes two rows (label, value) |
| dialogs < 70 columns | less padding; table inputs are laid out vertically |
| any narrow width | the top info row, hint bar and dashboard status bar drop minor items first; **quit, the file name (with `*`) and the error / warning count are always kept** |
| short terminal | lists inside dialogs shorten and wheels shrink to 3 rows so the bottom buttons are never cut off; ↑ ↓ in the form always move rows (the focused row scrolls into view) |

**Mouse:** wheel widgets can be clicked above / below the centre to scroll to that item, and the mouse
wheel scrolls them (up = previous value); buttons can be clicked; the mouse wheel also scrolls lists.

## Custom shortcut keys

The **command keys** can be changed; navigation keys (arrows, Enter, Esc, Tab, PgUp/PgDn, Home/End,
Space and `+` `-` inside the editor) and everything inside dialogs are fixed.

Add a `keys` section to `configs/tui_prefs.json` with only the keys you want to change:

```json
{"lang": "en", "keys": {"pause": "n", "module.combat": "1", "editor.search": "k"}}
```

| Action id | Default | Where |
|---|---|---|
| `quit` `pause` `log` `language` `toggle` `debug` | `q space l t shift+enter d` | dashboard |
| `module.combat` `.expedition` `.pvp` `.quest` `.scheduler` `.factory` `.passive_repair` `.ship_switcher` `.event_reset` `.general` | `c e p u s f r h v g` | dashboard and editor |
| `module.other` | `o` | editor only (unknown keys) |
| `editor.reset_default` `editor.undo` `editor.search` `editor.module_prev` `editor.module_next` | `d z / [ ]` | editor |

- A key is one lowercase letter or digit, one of `/ [ ] , . ;`, `space`, `f1`-`f12`, `shift+enter` or `ctrl+enter`.
- There are no `save` / `apply` actions any more; old entries with those names are ignored silently.
- A key can be used once per screen (the dashboard and the editor are separate screens, but the
  module keys count on both). Swapping two keys is fine.
- Mistakes never stop the CUI: a bad or conflicting override is dropped (the default is used) and
  every problem is written to the log on start-up with a warning.
- Keys are read once at start-up; restart the CUI after changing them.
- `python kcauto/kcauto_cui.py --show-keys` lists every action id with its current and default key.
- Module shortcut display: a key that is a letter of the label is highlighted in place (`c`ombat);
  any other key (`1`, `f5`, ...) is not marked at all. The hint bar follows the keymap; it does not list `log`.

## Languages

English is the default. Press `t` on the dashboard, or use `--lang CODE` / `KCAUTO_LANG`, to switch;
the choice is saved in `configs/tui_prefs.json` and the editor uses it the next time it opens.

To add a language, drop `kcauto/cui/locales/<code>.json` next to the existing ones:

```json
{
  "_name": "Display name",
  "fields": {"combat.enabled": {"label": "...", "help": "..."}},
  "messages": {"English source text": "translation"}
}
```

Anything that is not translated falls back to English, so a file can cover only part of the UI.
`tests/test_i18n.py` checks the bundled languages for missing fields / strings and mismatched
`{placeholders}`.

## Packaging

`cui/theme.tcss` and `cui/locales/*.json` must be bundled with the program. The packaged launcher
(`kcauto/kcauto_cui.py`, built by `tool/execution_packer/x_packer.sh` / `exe_packer.bat`) uses:

```
--add-data "../../kcauto/cui/theme.tcss:cui" --add-data "../../kcauto/cui/locales:cui/locales" --collect-all textual
# on Windows use ; instead of : in --add-data
```

The destination must be the package directory `cui`: both files are found relative to the module
(`Path(__file__).parent`). The package is imported as the top-level `cui` (kcauto's own directory is on
`sys.path`, as for the rest of kcauto). In a packaged build the CUI changes to the folder holding the
launcher, starts `bin/kcauto_custom/kcauto_custom[.exe]` and never falls back to `python kcauto`.
