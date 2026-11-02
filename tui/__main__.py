"""Usage: python -m tui [--config PATH] [--template PATH] [--lang CODE] [--autostart]

Run from the kcauto_custom project root: the CUI starts kcauto from the current working
directory (``./bin/kcauto_custom/kcauto_custom`` or ``python kcauto``), like the old CUI.
kcauto reads its config via ``--cfg <config name without extension>``, so the file name
given to ``--config`` must be one kcauto can find (default configs/config_cui.json →
``--cfg config_cui``).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import i18n
from .store import ConfigLoadError, ConfigStore

DEFAULT_CONFIG = "configs/config_cui.json"
DEFAULT_TEMPLATE = "data/config/config_cui_template.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tui", description="kcauto_custom config editor and console"
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
        "--autostart",
        action="store_true",
        help="start kcauto right after opening (off by default)",
    )
    args = parser.parse_args(argv)
    if args.lang and i18n.normalize(args.lang) is None:
        print(
            f"Unknown language: {args.lang} (available: {', '.join(c for c, _ in i18n.available())})",
            file=sys.stderr,
        )
        return 2
    i18n.init(args.lang)

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

    runner = Runner(cwd=os.getcwd(), config_name=Path(args.config).stem)
    KcautoCui(store, runner, autostart=args.autostart).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
