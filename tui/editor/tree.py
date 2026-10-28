"""JSON 樹狀表格編輯的純邏輯(不依賴 Textual)。

用在結構不固定的設定:``ship_switcher.slots``、以及 schema 不認得的 key。
畫面把樹攤平成一列一個節點:

    ▾ 1                     object {2}
        ship_id             int     12345
      ▸ rules               list [3]
    ▸ 2                     object {1}

所有修改函式都「就地」修改傳入的樹並回傳新的根(根本身被取代時才會是新物件),
呼叫端應先 ``copy.deepcopy`` 出工作副本。路徑是 key / 索引組成的 tuple;``()`` 是根。
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Optional

from .model import cell_len, clip_cells, pad_cells

Path = tuple

KINDS = ("str", "int", "float", "bool", "null", "object", "list")
CONTAINERS = ("object", "list")


def kind_of(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "list"
    return "str"


def default_for(kind: str) -> Any:
    return {"str": "", "int": 0, "float": 0.0, "bool": False, "null": None,
            "object": {}, "list": []}[kind]


def convert(value: Any, kind: str) -> Any:
    """盡量保留內容地換型別:"12"→12、1→"1"、0→False;換不過去就用該型別的預設值。"""
    if kind_of(value) == kind:
        return value
    if kind == "str":
        return "" if value is None else (str(value).lower() if isinstance(value, bool)
                                         else str(value) if not isinstance(value, (dict, list))
                                         else "")
    if kind == "int":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str) and re.fullmatch(r"\s*-?\d+\s*", value):
            return int(value)
    if kind == "float":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
    if kind == "bool":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value != 0
        if isinstance(value, str) and value.strip().lower() in ("true", "false"):
            return value.strip().lower() == "true"
    return default_for(kind)


def is_container(value: Any) -> bool:
    return isinstance(value, (dict, list))


# ---------------------------------------------------------------------- #
# 存取
# ---------------------------------------------------------------------- #
def get_at(root: Any, path: Path) -> Any:
    node = root
    for step in path:
        node = node[step]
    return node


def set_at(root: Any, path: Path, value: Any) -> Any:
    if not path:
        return value
    get_at(root, path[:-1])[path[-1]] = value
    return root


def delete_at(root: Any, path: Path) -> Any:
    if not path:
        return root
    parent = get_at(root, path[:-1])
    if isinstance(parent, dict):
        del parent[path[-1]]
    else:
        parent.pop(path[-1])
    return root


def unique_key(existing: Any, base: str = "new") -> str:
    if base not in existing:
        return base
    n = 2
    while f"{base}_{n}" in existing:
        n += 1
    return f"{base}_{n}"


def key_error(parent: dict, key: str, current: Optional[str] = None) -> Optional[str]:
    if not key.strip():
        return "Key cannot be empty"
    if key != current and key in parent:
        return f"Key “{key}” already exists"
    return None


def add_child(root: Any, parent_path: Path, key: Optional[str], value: Any) -> Path:
    """在容器下新增子項,回傳新子項的路徑。dict 需要 key;list 附加在最後。"""
    parent = get_at(root, parent_path)
    if isinstance(parent, dict):
        if key is None:
            raise ValueError("object child needs a key")
        parent[key] = value
        return parent_path + (key,)
    parent.append(value)
    return parent_path + (len(parent) - 1,)


def rename_key(root: Any, path: Path, new_key: str) -> Path:
    """改 key 並保持原本的順序。"""
    parent = get_at(root, path[:-1])
    if not isinstance(parent, dict):
        raise ValueError("only object keys can be renamed")
    items = [(new_key if k == path[-1] else k, v) for k, v in parent.items()]
    parent.clear()
    parent.update(items)
    return path[:-1] + (new_key,)


def parent_path(path: Path) -> Path:
    return path[:-1]


# ---------------------------------------------------------------------- #
# 攤平成一列一個節點
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class TreeRow:
    path: Path
    depth: int
    key: Any
    kind: str
    value: Any
    expandable: bool
    expanded: bool


def children_of(value: Any) -> list[tuple[Any, Any]]:
    if isinstance(value, dict):
        return list(value.items())
    if isinstance(value, list):
        return list(enumerate(value))
    return []


def flatten(root: Any, expanded: set[Path]) -> list[TreeRow]:
    """根本身不列出,從根的子項開始(depth 0)。"""
    rows: list[TreeRow] = []

    def walk(value: Any, path: Path, depth: int) -> None:
        for key, child in children_of(value):
            child_path = path + (key,)
            kind = kind_of(child)
            can_open = kind in CONTAINERS
            is_open = can_open and child_path in expanded
            rows.append(TreeRow(child_path, depth, key, kind, child, can_open, is_open))
            if is_open:
                walk(child, child_path, depth + 1)

    walk(root, (), 0)
    return rows


def all_container_paths(root: Any) -> set[Path]:
    out: set[Path] = set()

    def walk(value: Any, path: Path) -> None:
        for key, child in children_of(value):
            if is_container(child):
                out.add(path + (key,))
                walk(child, path + (key,))

    walk(root, ())
    return out


def initial_expanded(root: Any, limit: int = 60) -> set[Path]:
    """內容不多就全部展開,太多就只展開第一層。"""
    everything = all_container_paths(root)
    if len(flatten(root, everything)) <= limit:
        return everything
    return {p for p in everything if len(p) == 1}


def path_text(path: Path) -> str:
    out = ""
    for step in path:
        out += f"[{step}]" if isinstance(step, int) else (("." if out else "") + str(step))
    return out or "(root)"


# ---------------------------------------------------------------------- #
# 顯示
# ---------------------------------------------------------------------- #
def value_text(row: TreeRow, width: int = 40) -> str:
    v = row.value
    if row.kind == "object":
        return f"{{{len(v)}}}"
    if row.kind == "list":
        return f"[{len(v)}]"
    if row.kind == "bool":
        return "on" if v else "off"
    if row.kind == "null":
        return "null"
    if row.kind == "str":
        return clip_cells('"' + v + '"', width)
    return str(v)


def key_text(row: TreeRow) -> str:
    return f"[{row.key}]" if isinstance(row.key, int) else str(row.key)


def row_text(row: TreeRow, key_width: int, width: int) -> str:
    """`  ▾ key        type   value`;太窄時省略型別欄。"""
    indent = "  " * row.depth
    mark = ("▾ " if row.expanded else "▸ ") if row.expandable else "  "
    left = indent + mark + key_text(row)
    left = pad_cells(left, key_width)
    rest = max(4, width - key_width - 2)
    if rest >= 16:
        return f"{left}  {pad_cells(row.kind, 6)} {value_text(row, rest - 7)}"
    return f"{left}  {value_text(row, rest)}"


def key_column_width(rows: list[TreeRow], width: int) -> int:
    longest = max((cell_len("  " * r.depth + "▸ " + key_text(r)) for r in rows), default=8)
    return max(8, min(longest + 1, max(8, width // 2)))


def make_working_copy(value: Any) -> Any:
    return copy.deepcopy(value)
