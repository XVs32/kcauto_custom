"""Usage: python kcauto/kcauto_cui.py [--config PATH] [--template PATH] [--lang CODE] [--show-keys] [--autostart] [--debug-output]

Run from the kcauto_custom project root: the CUI starts kcauto from the current working
directory (``./bin/kcauto_custom/kcauto_custom`` or ``python kcauto`` when running from source), like the old CUI.
kcauto reads its config via ``--cfg <config name without extension>``, so the file name
given to ``--config`` must be one kcauto can find (default configs/config_cui.json →
``--cfg config_cui``).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import i18n, keymap, prefs
from .store import ConfigLoadError, ConfigStore

DEFAULT_CONFIG = "configs/config_cui.json"
DEFAULT_TEMPLATE = "template/configs/config_cui.json"


def _enter_project_root() -> None:
    """Packaged build: the launcher sits in the project root, so work from there whatever the shell's cwd is
    (config, data/, noro6 and ``bin/kcauto_custom`` are all found relative to it)."""
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).resolve().parent)


def main(argv: list[str] | None = None) -> int:
    _enter_project_root()
    parser = argparse.ArgumentParser(
        prog="kcauto_cui", description="kcauto_custom config editor and console"
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help=f"config file path (default {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE,
        help=f"template file path (default {DEFAULT_TEMPLATE})",
    )
    parser.add_argument(
        "--lang",
        default=None,
        metavar="CODE",
        help="editor language: "
        + ", ".join(c for c, _ in i18n.available())
        + " (default en; or set KCAUTO_LANG, or press t on the dashboard)",
    )
    parser.add_argument(
        "--show-keys",
        action="store_true",
        help="print every shortcut key (current and default) and exit",
    )
    parser.add_argument(
        "--autostart",
        action="store_true",
        help="start kcauto right after opening (off by default)",
    )
    parser.add_argument(
        "--debug-output",
        action="store_true",
        help="start in debug mode: kcauto is started with --debug-output "
        "(also remembered from the dashboard toggle)",
    )
    args = parser.parse_args(argv)
    if args.lang and i18n.normalize(args.lang) is None:
        print(
            f"Unknown language: {args.lang} (available: {', '.join(c for c, _ in i18n.available())})",
            file=sys.stderr,
        )
        return 2
    i18n.init(args.lang)
    # The shortcut keys must be loaded before anything that builds key bindings is imported.
    keys = keymap.init()
    if args.show_keys:
        print(keys.describe())
        for problem in keys.problems:
            print(f"warning: {problem}", file=sys.stderr)
        return 0

    try:
        store = ConfigStore(args.config, args.template)
    except ConfigLoadError as exc:
        print(f"Cannot load config: {exc}", file=sys.stderr)
        return 2

    try:
        from .app import KcautoCui
        from .runner import Runner
    except ImportError as exc:
        print(
            f"Missing dependency: {exc}\nPlease run: pip install textual psutil",
            file=sys.stderr,
        )
        return 3

    debug = args.debug_output or prefs.load_bool("debug")
    runner = Runner(cwd=os.getcwd(), config_name=Path(args.config).stem, debug=debug)
    KcautoCui(store, runner, autostart=args.autostart).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
