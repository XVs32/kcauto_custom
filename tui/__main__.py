"""用法:python -m tui [--config PATH] [--template PATH] [--autostart]

請在 kcauto_custom 的專案根目錄執行:CUI 會以目前的工作目錄啟動 kcauto
(``./bin/kcauto_custom/kcauto_custom`` 或 ``python kcauto``),與舊版 CUI 相同。
kcauto 以 ``--cfg <設定檔名稱(不含副檔名)>`` 讀取設定,因此 ``--config`` 的檔名
必須是 kcauto 找得到的設定檔(預設 configs/config_cui.json → ``--cfg config_cui``)。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .store import ConfigLoadError, ConfigStore

DEFAULT_CONFIG = "configs/config_cui.json"
DEFAULT_TEMPLATE = "data/config/config_cui_template.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tui",
                                     description="kcauto_custom 設定編輯器與控制台")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help=f"設定檔路徑(預設 {DEFAULT_CONFIG})")
    parser.add_argument("--template", default=DEFAULT_TEMPLATE,
                        help=f"模板檔路徑(預設 {DEFAULT_TEMPLATE})")
    parser.add_argument("--autostart", action="store_true",
                        help="開啟後立刻啟動 kcauto(預設不會自動啟動)")
    args = parser.parse_args(argv)

    try:
        store = ConfigStore(args.config, args.template)
    except ConfigLoadError as exc:
        print(f"無法載入設定:{exc}", file=sys.stderr)
        return 2

    try:
        from .app import KcautoCui
        from .runner import Runner
    except ImportError as exc:
        print(f"缺少相依套件:{exc}\n請先執行 pip install textual psutil",
              file=sys.stderr)
        return 3

    runner = Runner(cwd=os.getcwd(), config_name=Path(args.config).stem)
    KcautoCui(store, runner, autostart=args.autostart).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
