"""讀取 noro6 設定檔(configs/noro6/noro6),找出出擊海域有哪些「指定目標節點」的預設。

檔案格式與 fleet/noro6.py 相同:LZString(UTF-16)壓縮的 JSON,
``savedata`` 是資料夾樹,葉節點的 ``name`` 就是預設名稱,例如
``B-2-2``(2-2 一般預設)、``B-2-2-A``(2-2 目標節點 A)、``B-7-2-G``。
名稱以 ``-bak`` 結尾的會被 kcauto 略過,這裡也一樣(連同其子項)。

這裡不直接 import fleet.noro6:它會連帶載入 constants、ships、logger 等整個
kcauto 本體,而 CUI 的資料層不應依賴它們。解壓縮的實作只有幾十行,獨立維護。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

NORO6_FILES = ("configs/noro6/noro6", "template/configs/noro6/noro6")

# B-<世界>-<編號>[-<節點>]:一般出擊預設。任務用的 By2-1-1、2610B2-1-2 不會符合。
_SORTIE_PRESET = re.compile(r"B-([A-Za-z0-9]+)-(\d+)(?:-([A-Za-z0-9]+))?")


def decompress_utf16(compressed: str) -> Optional[str]:
    """LZString.decompressFromUTF16。格式不合時回傳 None。"""
    if not compressed:
        return ""
    length = len(compressed)

    def get(i: int) -> int:
        return ord(compressed[i]) - 32 if i < length else 0

    reset = 16384
    dictionary: dict[int, str] = {}
    enlarge, size, nbits = 4, 4, 3
    state = {"val": get(0), "pos": reset, "idx": 1}

    def read(count: int) -> int:
        bits, power, limit = 0, 1, 1 << count
        while power != limit:
            hit = state["val"] & state["pos"]
            state["pos"] >>= 1
            if state["pos"] == 0:
                state["pos"] = reset
                state["val"] = get(state["idx"])
                state["idx"] += 1
            if hit:
                bits |= power
            power <<= 1
        return bits

    first = read(2)
    if first == 0:
        c = chr(read(8))
    elif first == 1:
        c = chr(read(16))
    else:
        return ""
    dictionary[3] = c
    w = c
    out = [c]
    while True:
        if state["idx"] > length:
            return ""
        code = read(nbits)
        if code == 0:
            dictionary[size] = chr(read(8))
            size += 1
            code = size - 1
            enlarge -= 1
        elif code == 1:
            dictionary[size] = chr(read(16))
            size += 1
            code = size - 1
            enlarge -= 1
        elif code == 2:
            return "".join(out)
        if enlarge == 0:
            enlarge = 1 << nbits
            nbits += 1
        if code in dictionary:
            entry = dictionary[code]
        elif code == size:
            entry = w + w[0]
        else:
            return None
        out.append(entry)
        dictionary[size] = w + entry[0]
        size += 1
        enlarge -= 1
        w = entry
        if enlarge == 0:
            enlarge = 1 << nbits
            nbits += 1


def find_file(root: Path | str = ".") -> Optional[Path]:
    base = Path(root)
    for rel in NORO6_FILES:
        path = base / rel
        if path.is_file():
            return path
    return None


def _collect(node: Any, out: list[str]) -> None:
    if not isinstance(node, dict):
        return
    name = node.get("name")
    if isinstance(name, str) and name.endswith("-bak"):
        return
    if node.get("isDirectory") is True:
        for child in node.get("childItems") or []:
            _collect(child, out)
    elif isinstance(name, str):
        out.append(name)


def load_preset_names(root: Path | str = ".") -> list[str]:
    """檔案內所有(非 -bak)預設名稱,依檔案順序。讀不到或格式不對時回傳空清單。"""
    path = find_file(root)
    if path is None:
        return []
    try:
        text = decompress_utf16(path.read_text(encoding="utf-8"))
        data = json.loads(text) if text else None
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    names: list[str] = []
    _collect(data.get("savedata"), names)
    return names


def sortie_nodes(names: list[str]) -> dict[tuple[str, int], list[str]]:
    """{(世界, 編號): [有指定目標節點的預設的節點名稱…]},例如 ("2", 2) → ["A"]。"""
    index: dict[tuple[str, int], list[str]] = {}
    for name in names:
        m = _SORTIE_PRESET.fullmatch(name)
        if m and m.group(3):
            nodes = index.setdefault((m.group(1), int(m.group(2))), [])
            if m.group(3) not in nodes:
                nodes.append(m.group(3))
    return index


def load_sortie_nodes(root: Path | str = ".") -> dict[tuple[str, int], list[str]]:
    return sortie_nodes(load_preset_names(root))
