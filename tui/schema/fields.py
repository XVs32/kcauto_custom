"""kcauto_custom 設定檔欄位定義(依 Wiki Ch5,共 61 個 key)。

這份 schema 是 CUI 的單一事實來源:
  * 編輯器依 ``kind`` 選擇控制項,依 ``group`` 分區,顯示 ``label`` / ``help``。
  * ``Field.validate`` 負責單一欄位驗證;跨欄位規則在 ``rules.py``。
  * ``advanced`` 的欄位在儀表板預設折疊;``danger`` 的欄位修改前需二次確認。

新增設定只需要在 ``_FIELDS`` 加一筆;``tests/test_schema.py`` 會比對
Ch5 的欄位清單,漏掉就會失敗。
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

from .scheduler_rule import check_rule


class Kind(str, Enum):
    BOOL = "bool"        # 開關
    ENUM = "enum"        # 單選(可 nullable)
    INT = "int"          # 帶範圍整數
    INT_STR = "int_str"  # 整數或字串(例如秘書艦 ID,兩種寫法皆可)
    STR = "str"          # 字串(可帶 pattern)
    LIST = "list"        # 字串/整數陣列
    PRESET = "preset"    # 1~15、"auto" 或 None(艦隊 preset)
    RECIPE = "recipe"    # 4 個整數 [油, 彈, 鋼, 鋁]
    OBJECT = "object"    # 任意 JSON 物件


MODULES = (
    "general", "combat", "expedition", "pvp", "quest",
    "factory", "scheduler", "passive_repair", "ship_switcher", "event_reset",
)

FORMATIONS = (
    "line_ahead", "double_line", "diamond", "echelon", "line_abreast",
    "vanguard", "combined_fleet_1", "combined_fleet_2",
    "combined_fleet_3", "combined_fleet_4",
)
FLEET_MODES = ("standard", "strike", "tcf", "ctf", "stf")
COMBINED_FLEET_MODES = ("tcf", "ctf", "stf")
INTERACTION_MODES = ("chrome_driver", "direct_control", "poi")

_NODE = r"[A-Za-z0-9_]+"
_ID = r"[A-Za-z0-9_]+"
_PRESET_ITEM = r"auto|[1-9]|1[0-5]"


def _is_int(value: Any) -> bool:
    # bool 是 int 的子類別,必須排除
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class Field:
    key: str
    kind: Kind
    default: Any
    label: str
    help: str
    group: str = "basic"
    choices: tuple = ()                  # ENUM 的合法值
    nullable: bool = False               # ENUM / PRESET 是否允許 None
    min: Optional[int] = None            # INT / RECIPE 元素下限
    max: Optional[int] = None            # INT / RECIPE 元素上限
    pattern: Optional[str] = None        # STR 整體、LIST 每個元素的 regex
    pattern_hint: str = ""               # pattern 不符時顯示的格式提示
    lengths: tuple = ()                  # LIST 允許的長度(空 = 不限)
    item_check: Optional[Callable[[Any], Optional[str]]] = None
    advanced: bool = False
    danger: bool = False

    @property
    def module(self) -> str:
        return self.key.split(".", 1)[0]

    @property
    def name(self) -> str:
        return self.key.split(".", 1)[1]

    def make_default(self) -> Any:
        return copy.deepcopy(self.default)

    # ------------------------------------------------------------------ #
    def validate(self, value: Any) -> list[str]:
        """回傳錯誤訊息清單;空清單代表合法。"""
        check = getattr(self, f"_check_{self.kind.value}")
        return check(value)

    def _check_bool(self, value: Any) -> list[str]:
        return [] if isinstance(value, bool) else ["必須是 true 或 false"]

    def _check_enum(self, value: Any) -> list[str]:
        if value is None:
            return [] if self.nullable else ["不可為 null"]
        if value in self.choices and isinstance(value, str):
            return []
        return ["必須是以下其一:" + "、".join(self.choices)]

    def _check_int(self, value: Any) -> list[str]:
        if not _is_int(value):
            return ["必須是整數"]
        return self._range_errors(value)

    def _range_errors(self, value: int) -> list[str]:
        if self.min is not None and value < self.min:
            return [f"不可小於 {self.min}"]
        if self.max is not None and value > self.max:
            return [f"不可大於 {self.max}"]
        return []

    def _check_int_str(self, value: Any) -> list[str]:
        if _is_int(value):
            return self._range_errors(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return ["不可為空字串"]
            if re.fullmatch(r"-?\d+", text):   # "1234" 視同整數,套用範圍
                return self._range_errors(int(text))
            return []
        return ["必須是整數或字串"]

    def _check_str(self, value: Any) -> list[str]:
        if not isinstance(value, str):
            return ["必須是字串"]
        if self.pattern and not re.fullmatch(self.pattern, value):
            return [self.pattern_hint or "格式不符"]
        return []

    def _check_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return ["必須是陣列"]
        errors: list[str] = []
        if self.lengths and len(value) not in self.lengths:
            allowed = "、".join(str(n) for n in self.lengths)
            errors.append(f"元素數量必須是 {allowed} 個(目前 {len(value)} 個)")
        for index, item in enumerate(value, start=1):
            if isinstance(item, bool) or not isinstance(item, (str, int)):
                errors.append(f"第 {index} 項必須是字串或整數")
                continue
            if self.pattern and not re.fullmatch(self.pattern, str(item)):
                hint = self.pattern_hint or "格式不符"
                errors.append(f"第 {index} 項「{item}」:{hint}")
            if self.item_check is not None:
                message = self.item_check(item)
                if message:
                    errors.append(f"第 {index} 項「{item}」:{message}")
        return errors

    def _check_preset(self, value: Any) -> list[str]:
        if value is None:
            return [] if self.nullable else ["不可為 null"]
        if value == "auto":
            return []
        # 0 是文件中的預設值(代表未指定),因此允許 0~15
        if _is_int(value) and 0 <= value <= 15:
            return []
        return ["必須是 1~15、auto 或 null"]

    def _check_recipe(self, value: Any) -> list[str]:
        if not isinstance(value, list) or len(value) != 4:
            return ["必須是 4 個整數 [油, 彈, 鋼, 鋁]"]
        errors = []
        for label, item in zip(("油", "彈", "鋼", "鋁"), value):
            if not _is_int(item):
                errors.append(f"{label} 必須是整數")
            else:
                errors.extend(f"{label} {e}" for e in self._range_errors(item))
        return errors

    def _check_object(self, value: Any) -> list[str]:
        return [] if isinstance(value, dict) else ["必須是 JSON 物件"]


# ---------------------------------------------------------------------- #
# 欄位建構小工具
# ---------------------------------------------------------------------- #
def _bool(key, default, label, help, **kw):
    return Field(key, Kind.BOOL, default, label, help, **kw)


def _int(key, default, label, help, **kw):
    return Field(key, Kind.INT, default, label, help, **kw)


def _int_str(key, default, label, help, **kw):
    return Field(key, Kind.INT_STR, default, label, help, **kw)


def _enum(key, default, label, help, choices, **kw):
    return Field(key, Kind.ENUM, default, label, help, choices=tuple(choices), **kw)


def _list(key, label, help, **kw):
    return Field(key, Kind.LIST, [], label, help, **kw)


_NODE_HINT = "節點名稱只能包含英數字與底線"

_FIELDS: tuple[Field, ...] = (
    # ------------------------------ general ------------------------------ #
    _enum("general.interaction_mode", "chrome_driver", "操作模式",
          "kcauto 與遊戲互動的方式:chrome_driver 透過 Chrome DevTools、"
          "direct_control 使用桌面滑鼠、poi 使用 POI 的 API Forwarder 外掛。",
          INTERACTION_MODES),
    _int("general.jst_offset", 0, "JST 時差(小時)",
         "排程與時間相關操作相對日本標準時間的偏移。", min=-20, max=20),
    _int("general.chrome_dev_port", 9222, "Chrome DevTools 連接埠",
         "Chrome DevTools Protocol 使用的連接埠。不確定請勿更動。",
         group="ports", min=0, max=65535, advanced=True),
    _int("general.poi_api_port", 9223, "POI API 連接埠",
         "POI API 轉發使用的連接埠。不確定請勿更動。",
         group="ports", min=0, max=65535, advanced=True),
    _int("general.poi_control_port", 38591, "POI 控制連接埠",
         "interaction_mode 為 poi 時,截圖與輸入使用的本機連接埠。",
         group="ports", min=0, max=65535, advanced=True),
    _bool("general.paused", False, "啟動時暫停",
          "kcauto 是否以暫停狀態啟動。目前尚無作用(Wiki 標註 2025/07/17),"
          "CUI 請改用空白鍵暫停。", advanced=True),

    # ------------------------------- combat ------------------------------ #
    _bool("combat.enabled", False, "啟用出擊", "是否啟用出擊模組。"),
    Field("combat.sortie_map", Kind.STR, "1-1", "出擊海域",
          "地圖編號,例如 1-1、3-5、6-4、E-1;後面可再接目標節點,例如 2-2-A、7-2-G"
          "(需要 noro6 內有對應的預設);填 auto 自動選擇海域。",
          pattern=r"auto|[A-Za-z0-9]+-\d+(-[A-Za-z0-9]+)?",
          pattern_hint="格式應為 1-1、E-1、2-2-A 這類編號,或 auto"),
    _enum("combat.fleet_mode", "standard", "艦隊模式",
          "standard 單一艦隊;strike 遊擊部隊(使用第 3 艦隊);"
          "tcf 輸送護衛;ctf 機動部隊;stf 水上打擊部隊。", FLEET_MODES),
    _list("combat.fleet_presets", "艦隊 preset",
          "出擊使用的遊戲內艦隊 preset(1~15),或 auto 自動選擇。",
          pattern=_PRESET_ITEM, pattern_hint="只能是 1~15 或 auto"),
    _bool("combat.check_fatigue", True, "檢查疲勞",
          "出擊前是否檢查艦娘疲勞度。", group="fatigue"),
    _bool("combat.check_lbas_fatigue", True, "檢查基地航空隊疲勞",
          "出擊前是否檢查基地航空隊(LBAS)疲勞度。", group="fatigue"),
    _bool("combat.clear_stop", False, "海域通關後停止",
          "地圖通關後是否停止出擊。"),
    _bool("combat.port_check", False, "出擊前檢查母港容量",
          "出擊前是否檢查母港容量。"),
    _bool("combat.reserve_repair_dock", True, "保留入渠位",
          "是否保留入渠位供緊急修理使用。", group="repair"),
    _int("combat.retreat_limit", 4, "撤退損傷等級",
         "達到此損傷等級時撤退。0 無損、1 擦傷、2 小破、3 中破、4 大破。",
         group="repair", min=0, max=4),
    _int("combat.repair_limit", 3, "修理損傷等級",
         "達到此損傷等級時自動修理。", group="repair", min=0, max=4),
    _int("combat.repair_bucket_threshold", 500, "高速修復材保留量",
         "高速修復材低於此數量時不使用。", group="repair", min=0),
    _int("combat.repair_timelimit_hours", 0, "自然修復上限(小時)",
         "超過此時數才使用高速修復材,與分鐘合計。", group="repair", min=0),
    _int("combat.repair_timelimit_minutes", 0, "自然修復上限(分鐘)",
         "超過此分鐘數才使用高速修復材。", group="repair", min=0, max=59),
    _list("combat.retreat_points", "撤退節點",
          "艦隊應撤退的節點名稱,例如 A、B、C。",
          group="routing", pattern=_NODE, pattern_hint=_NODE_HINT),
    _list("combat.push_nodes", "強行進擊節點(危險)",
          "不論損傷都繼續前進的節點。大破進擊會造成艦娘沉沒,請謹慎使用。",
          group="routing", pattern=_NODE, pattern_hint=_NODE_HINT,
          danger=True),
    _list("combat.node_selects", "分歧點選路",
          "分歧點的路線選擇,格式 來源>目標,例如 A>B。",
          group="routing", pattern=rf"{_NODE}>{_NODE}",
          pattern_hint="格式應為 來源>目標,例如 A>B"),
    _list("combat.node_formations", "節點陣型",
          "各節點使用的陣型,格式 節點:陣型,例如 A:line_ahead。",
          group="routing",
          pattern=rf"{_NODE}:(?:{'|'.join(FORMATIONS)})",
          pattern_hint="格式應為 節點:陣型,陣型須為 " + "/".join(FORMATIONS)),
    _list("combat.node_night_battles", "節點夜戰",
          "各節點是否夜戰,格式 節點:True 或 節點:False。",
          group="routing", pattern=rf"{_NODE}:(?:True|False)",
          pattern_hint="格式應為 節點:True 或 節點:False"),
    _list("combat.node_smoke", "煙幕節點", "使用煙幕的節點名稱。",
          group="routing", pattern=_NODE, pattern_hint=_NODE_HINT),
    _list("combat.lbas_groups", "啟用的基地航空隊",
          "要啟用的基地航空隊編號(1、2、3)。",
          group="lbas", pattern=r"[1-3]", pattern_hint="只能是 1、2 或 3"),
    _list("combat.lbas_group_1_nodes", "第 1 隊目標節點",
          "第 1 基地航空隊的目標,必須剛好 0 或 2 個節點,例如 A、A。",
          group="lbas", pattern=_NODE, pattern_hint=_NODE_HINT,
          lengths=(0, 2)),
    _list("combat.lbas_group_2_nodes", "第 2 隊目標節點",
          "第 2 基地航空隊的目標,必須剛好 0 或 2 個節點。",
          group="lbas", pattern=_NODE, pattern_hint=_NODE_HINT,
          lengths=(0, 2)),
    _list("combat.lbas_group_3_nodes", "第 3 隊目標節點",
          "第 3 基地航空隊的目標,必須剛好 0 或 2 個節點。",
          group="lbas", pattern=_NODE, pattern_hint=_NODE_HINT,
          lengths=(0, 2)),
    _bool("combat.override", False, "允許執行期覆寫",
          "是否允許在執行期間覆寫設定。", advanced=True),

    # ----------------------------- expedition ---------------------------- #
    _bool("expedition.enabled", True, "啟用遠征", "是否啟用遠征模組。"),
    _list("expedition.fleet_2", "第 2 艦隊遠征",
          "第 2 艦隊要執行的遠征編號,或 auto 自動選擇。",
          group="fleets", pattern=_ID, pattern_hint="只能包含英數字與底線"),
    _list("expedition.fleet_3", "第 3 艦隊遠征",
          "第 3 艦隊要執行的遠征編號,或 auto 自動選擇。",
          group="fleets", pattern=_ID, pattern_hint="只能包含英數字與底線"),
    _list("expedition.fleet_4", "第 4 艦隊遠征",
          "第 4 艦隊要執行的遠征編號,或 auto 自動選擇。",
          group="fleets", pattern=_ID, pattern_hint="只能包含英數字與底線"),
    Field("expedition.fleet_preset", Kind.ENUM, None, "艦隊 preset 模式",
          "目前只支援 auto 或不使用(null)。", group="fleets",
          choices=("auto",), nullable=True),
    _int("expedition.desire_oil", 350000, "燃料目標量",
         "遠征要維持的燃料目標量。", group="resources", min=0, max=350000),
    _int("expedition.desire_ammo", 350000, "彈藥目標量",
         "遠征要維持的彈藥目標量。", group="resources", min=0, max=350000),
    _int("expedition.desire_steel", 350000, "鋼材目標量",
         "遠征要維持的鋼材目標量。", group="resources", min=0, max=350000),
    _int("expedition.desire_bauxite", 350000, "鋁土目標量",
         "遠征要維持的鋁土目標量。", group="resources", min=0, max=350000),
    _int("expedition.desire_bucket", 3000, "高速修復材目標量",
         "遠征要維持的高速修復材目標量。", group="resources", min=0, max=3000),

    # -------------------------------- pvp -------------------------------- #
    _bool("pvp.enabled", False, "啟用演習",
          "是否啟用演習。出擊艦隊為聯合艦隊時不可啟用。"),
    Field("pvp.fleet_preset", Kind.PRESET, 0, "演習艦隊 preset",
          "演習使用的艦隊 preset(1~15)、auto 或 null。", nullable=True),

    # ------------------------------- quest ------------------------------- #
    _bool("quest.enabled", True, "啟用任務", "是否自動接取並完成任務。"),
    _list("quest.quests", "任務清單",
          "要自動接取並完成的任務 ID,例如 Bd1、Bw1、C2。",
          pattern=_ID, pattern_hint="只能包含英數字與底線"),

    # ------------------------------ factory ------------------------------ #
    _bool("factory.enabled", False, "啟用工廠", "是否啟用建造與開發。"),
    Field("factory.build_recipe", Kind.RECIPE, [30, 30, 30, 30], "建造配方",
          "建造艦娘的資源配方 [燃料, 彈藥, 鋼材, 鋁土]。",
          group="build", min=0),
    _int_str("factory.build_secretary", 1234, "建造旗艦(秘書艦)",
         "建造時使用的秘書艦 ID。", group="build", min=0),
    Field("factory.develop_recipe", Kind.RECIPE, [10, 10, 10, 10], "開發配方",
          "開發裝備的資源配方 [燃料, 彈藥, 鋼材, 鋁土]。",
          group="develop", min=0),
    _int_str("factory.develop_secretary", 1234, "開發旗艦(秘書艦)",
         "開發時使用的秘書艦 ID。", group="develop", min=0),

    # ----------------------------- scheduler ----------------------------- #
    _bool("scheduler.enabled", True, "啟用排程", "是否啟用排程系統。"),
    _list("scheduler.rules", "排程規則",
          "格式 condition:value:action:module[:extra],"
          "例如 time:0230:stop:kcauto、sorties_run:15:stop:combat。",
          item_check=check_rule),

    # --------------------------- passive_repair -------------------------- #
    _bool("passive_repair.enabled", False, "啟用被動修理",
          "是否啟用入渠位自動管理。"),
    _int("passive_repair.repair_threshold", 1, "修理損傷等級",
         "達到此損傷等級才觸發被動修理(1~4)。", min=1, max=4),
    _int("passive_repair.slots_to_reserve", 2, "保留入渠位數量",
         "保留供緊急修理的入渠位數量。", min=0),

    # --------------------------- ship_switcher --------------------------- #
    _bool("ship_switcher.enabled", False, "啟用艦娘切換",
          "是否啟用自動切換艦娘。"),
    Field("ship_switcher.slots", Kind.OBJECT, {}, "切換規則",
          "各艦隊欄位的切換規則(JSON 物件)。", advanced=True),

    # ---------------------------- event_reset ---------------------------- #
    _bool("event_reset.enabled", False, "啟用活動重置", "是否啟用活動海域重置。"),
    _int("event_reset.farm_difficulty", 2, "刷圖難度",
         "刷圖時使用的難度(1~4)。", min=1, max=4),
    _int("event_reset.reset_difficulty", 3, "重置難度",
         "刷圖完成後重置到的難度(1~4)。", min=1, max=4),
    _int("event_reset.frequency", 3, "重置頻率",
         "刷圖幾輪後觸發一次重置。", min=0),
)

SCHEMA: dict[str, Field] = {f.key: f for f in _FIELDS}
if len(SCHEMA) != len(_FIELDS):  # pragma: no cover - 開發期防呆
    raise RuntimeError("schema 內有重複的 key")


def fields_of(module: str) -> list[Field]:
    """依 schema 順序回傳某模組的欄位。"""
    return [f for f in _FIELDS if f.module == module]


def groups_of(module: str) -> list[str]:
    """回傳某模組的分區名稱(保持出現順序)。"""
    seen: list[str] = []
    for f in fields_of(module):
        if f.group not in seen:
            seen.append(f.group)
    return seen


def defaults() -> dict[str, Any]:
    return {f.key: f.make_default() for f in _FIELDS}
