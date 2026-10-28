"""ConfigStore:CUI 的設定資料層(與 UI、與 kcauto 行程皆無耦合)。

職責
  * 載入:schema 預設值 ← 模板檔 ← 使用者設定檔,逐層覆蓋。
  * 未知 key 一律保留並原樣寫回,避免新版 kcauto 加了欄位而被 CUI 吃掉。
  * 追蹤修改(dirty / changed_keys),可還原單一欄位或全部。
  * 驗證:單欄位 + 跨欄位,結果以 ``Issue`` 回報。
  * 存檔:先備份,再「寫暫存檔 → fsync → os.replace」,bot 不會讀到寫到一半的 JSON。
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from .schema import (
    SCHEMA,
    Issue,
    defaults,
    has_errors,
    validate_all,
    validate_cross,
    validate_field,
)

Listener = Callable[[Optional[str]], None]


class ConfigLoadError(Exception):
    """設定檔或模板無法讀取(不存在以外的原因,例如 JSON 損壞)。"""


class ConfigValidationError(Exception):
    """存檔時發現 error 等級的問題。"""

    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__("設定包含錯誤:\n" + "\n".join(str(i) for i in issues))


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ConfigLoadError(f"{path} 不是有效的 JSON:{exc}") from exc
    except OSError as exc:
        raise ConfigLoadError(f"無法讀取 {path}:{exc}") from exc
    if not isinstance(data, dict):
        raise ConfigLoadError(f"{path} 的最上層必須是 JSON 物件")
    return data


class ConfigStore:
    def __init__(
        self,
        path: os.PathLike | str,
        template_path: os.PathLike | str | None = None,
    ) -> None:
        self.path = Path(path)
        self.template_path = Path(template_path) if template_path else None
        self.is_new_file = False
        self._values: dict[str, Any] = {}
        self._saved: dict[str, Any] = {}
        self._unknown_order: list[str] = []
        self._listeners: list[Listener] = []
        self.load()

    # ------------------------------------------------------------------ #
    # 載入
    # ------------------------------------------------------------------ #
    def load(self) -> None:
        merged = defaults()
        if self.template_path is not None and self.template_path.is_file():
            merged.update(_read_json_object(self.template_path))

        self.is_new_file = not self.path.is_file()
        if not self.is_new_file:
            merged.update(_read_json_object(self.path))

        self._unknown_order = [k for k in merged if k not in SCHEMA]
        self._values = merged
        self._saved = copy.deepcopy(merged)
        self._notify(None)

    # ------------------------------------------------------------------ #
    # 讀寫
    # ------------------------------------------------------------------ #
    def get(self, key: str) -> Any:
        """回傳值的副本,外部修改不會影響內部狀態。"""
        return copy.deepcopy(self._values[key])

    def __contains__(self, key: str) -> bool:
        return key in self._values

    def keys(self) -> list[str]:
        return list(self._ordered_keys())

    def as_dict(self) -> dict[str, Any]:
        return {k: copy.deepcopy(self._values[k]) for k in self._ordered_keys()}

    def set(self, key: str, value: Any) -> list[Issue]:
        """設定欄位並回傳該欄位(含跨欄位)相關的問題。

        不合法的值仍會被保留(編輯器需要顯示使用者正在輸入的內容),
        是否允許存檔/套用由 ``save`` 決定。
        """
        value = copy.deepcopy(value)
        if key not in SCHEMA and key not in self._values:
            self._unknown_order.append(key)
        self._values[key] = value
        self._notify(key)
        return self.issues_for(key)

    def reset_key(self, key: str) -> None:
        """還原為 schema 預設值(未知欄位無預設,會被忽略)。"""
        field = SCHEMA.get(key)
        if field is not None:
            self.set(key, field.make_default())

    def revert_key(self, key: str) -> None:
        """還原為上次存檔(或載入)時的值。"""
        if key in self._saved:
            self._values[key] = copy.deepcopy(self._saved[key])
            self._notify(key)

    def revert_all(self) -> None:
        self._values = copy.deepcopy(self._saved)
        self._notify(None)

    # ------------------------------------------------------------------ #
    # 修改狀態
    # ------------------------------------------------------------------ #
    def changed_keys(self) -> list[str]:
        return [
            k for k in self._ordered_keys()
            if k not in self._saved or self._values[k] != self._saved[k]
        ]

    @property
    def is_dirty(self) -> bool:
        return self.is_new_file or bool(self.changed_keys())

    def is_changed(self, key: str) -> bool:
        return key not in self._saved or self._values.get(key) != self._saved[key]

    # ------------------------------------------------------------------ #
    # 驗證
    # ------------------------------------------------------------------ #
    def issues(self) -> list[Issue]:
        return validate_all(self._values)

    def issues_for(self, key: str) -> list[Issue]:
        found = validate_field(key, self._values.get(key))
        found += [i for i in validate_cross(self._values) if key in i.keys]
        return found

    def has_errors(self) -> bool:
        return has_errors(self.issues())

    # ------------------------------------------------------------------ #
    # 存檔
    # ------------------------------------------------------------------ #
    def save(self, *, force: bool = False, backup: bool = True) -> Path:
        """原子寫入設定檔。有 error 等級問題時拒絕,除非 ``force=True``。"""
        problems = [i for i in self.issues() if i.level == "error"]
        if problems and not force:
            raise ConfigValidationError(problems)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        if backup and self.path.is_file():
            self._write_backup()

        payload = json.dumps(self.as_dict(), indent=4, ensure_ascii=False) + "\n"
        fd, tmp_name = tempfile.mkstemp(
            prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, self.path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

        self._saved = copy.deepcopy(self._values)
        self.is_new_file = False
        self._notify(None)
        return self.path

    @property
    def backup_path(self) -> Path:
        return self.path.with_name(self.path.name + ".bak")

    def _write_backup(self) -> None:
        data = self.path.read_bytes()
        self.backup_path.write_bytes(data)

    # ------------------------------------------------------------------ #
    # 變更通知(給 UI 訂閱)
    # ------------------------------------------------------------------ #
    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def unsubscribe(self, listener: Listener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify(self, key: Optional[str]) -> None:
        for listener in list(self._listeners):
            listener(key)

    # ------------------------------------------------------------------ #
    def _ordered_keys(self) -> Iterable[str]:
        """schema 順序在前,未知欄位依原本出現順序接在後面。"""
        for key in SCHEMA:
            if key in self._values:
                yield key
        for key in self._unknown_order:
            if key in self._values:
                yield key
