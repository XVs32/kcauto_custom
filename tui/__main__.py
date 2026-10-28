"""用法:python -m tui [--config PATH] [--template PATH]"""
from __future__ import annotations

import argparse
import sys

from .store import ConfigLoadError, ConfigStore

DEFAULT_CONFIG = "configs/config_cui.json"
DEFAULT_TEMPLATE = "data/config/config_cui_template.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tui",
                                     description="kcauto_custom 設定編輯器")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help=f"設定檔路徑(預設 {DEFAULT_CONFIG})")
    parser.add_argument("--template", default=DEFAULT_TEMPLATE,
                        help=f"模板檔路徑(預設 {DEFAULT_TEMPLATE})")
    args = parser.parse_args(argv)

    try:
        store = ConfigStore(args.config, args.template)
    except ConfigLoadError as exc:
        print(f"無法載入設定:{exc}", file=sys.stderr)
        return 2

    try:
        from .app import KcautoCui
    except ImportError as exc:
        print(f"缺少相依套件:{exc}\n請先執行 pip install textual", file=sys.stderr)
        return 3

    KcautoCui(store).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
