"""Thin launcher for the kcauto_custom CUI (the real code is in the ``cui`` package next to this file).

From source (project root):  python kcauto/kcauto_cui.py [options]
Packaged:                    ./kcauto_cui [options]
"""

from cui.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
