import json
import re
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from kca_enums.enum_base import EnumBase
from util.json_data import JsonData
from util.logger import Log

# ---------------------------------------------------------------------------
# Naming format (value):  <quest>-<world>-<map>[-<node>]
#   quest : B | Bw1 / Bm1 / Bq8 / By2 ... | 2509B5 (event date + period)
#   world : number or E (EO)
#   map   : number
#   node  : A / Z / AA / A1 / ZZ ... (optional)
# Additionally reserves the special value "B-auto" (auto_map_select)
# ---------------------------------------------------------------------------
_VALUE_RE = re.compile(
    r"^(?P<quest>B[a-z]?\d*|\d{4}B\d+)"
    r"-(?P<world>\d+|E)"
    r"-(?P<map>\d+)"
    r"(?:-(?P<node>[A-Z]{1,2}\d*))?$"
)

# If you want to persist auto-added members, set a path here
# (e.g. Path("data/combat/map_enum_auto.json")).
# When None, the members only exist for the current process lifetime.
AUTO_SAVE_PATH: Path | None = None

_lock = threading.RLock()


def _derive_name(value: str) -> str:
    """Derive member name from value, following the same rules as existing
    entries in map_enum.json.

    Examples:
        B-1-2-A        -> W1_2_A
        B-E-1-A1       -> WE_1_A1
        Bq8-7-2-G      -> W7_2_G_Bq8
        2509B5-4-2     -> W4-2-2509B5   (date-style quest uses "-" separator)
    """
    quest, *rest = value.split("-")
    if quest == "B":
        return "W" + "_".join(rest)
    if quest[0].isdigit():
        return "W" + "-".join(rest) + "-" + quest
    return "W" + "_".join(rest) + "_" + quest


class MapEnum(EnumBase):
    @property
    def quest(self):
        quest = self.value.split("-")[0]
        if quest.startswith("B"):
            return quest[1:] or None  # "Bq8" -> "q8", "B" -> None
        return quest  # "2509B5" is the full quest identifier

    @property
    def world(self):
        world = self.value.split("-")[1]
        if world == "E":
            return world
        return int(world)

    @property
    def map(self):
        return int(self.value.split("-")[2])

    @property
    def world_and_map(self):
        if self.value != "auto":
            return self.value.split("-")[1] + "-" + self.value.split("-")[2]
        else:
            return "auto"
    
    @property
    def world_and_map_enum(self):
        if self.value != "auto":
            return self.__class__("B-" + self.world_and_map)
        else:
            return self.__class__.auto_map_select

    @property
    def world_and_map_enum(self):
        if self.value != "auto":
            return self.__class__("B-" + self.world_and_map)
        else:
            return self.__class__.auto_map_select

    @property
    def world_and_map_enum(self):
        if self.value != "auto":
            return self.__class__("B-" + self.world_and_map)
        else:
            return self.__class__.auto_map_select

    @property
    def world_and_map_and_node(self):
        if self.value != "auto":
            return self.value[self.value.index("-") + 1 :]
        else:
            return "auto"

    @property
    def without_quest(self):
        if self.value != "auto":
            return f"B{self.value[self.value.index('-') :]}"
        else:
            return "auto"

    @property
    def without_quest_enum(self):
        if self.value != "auto":
            return self.__class__("B" + self.value[self.value.index("-") :])
        else:
            return self.__class__.auto_map_select

    @property
    def without_quest_and_node(self):
        if self.value != "auto":
            return "B-" + self.value.split("-")[1] + "-" + self.value.split("-")[2]
        else:
            return "auto"

    @property
    def without_quest_and_node_enum(self):
        if self.value != "auto":
            return self.__class__(
                "B-" + self.value.split("-")[1] + "-" + self.value.split("-")[2]
            )
        else:
            return self.__class__.auto_map_select

    @property
    def is_map_variant(self):
        return len(self.value.split("-")) > 3

    @property
    def variant(self):
        if self.is_map_variant:
            return self.value.split("-")[3]
        else:
            return None

    @property
    def is_eo(self):
        return self.map >= 5

    # ------------------------------------------------------------------
    # Automatically register unknown members
    # ------------------------------------------------------------------
    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str) or not _VALUE_RE.match(value):
            Log.log_error(f"MapEnum: Unknown map value '{value}' encountered.")
            return None

        with _lock:
            # Another thread may have already created it
            existing = cls._value2member_map_.get(value)
            if existing is not None:
                return existing

            member = cls._register_member(_derive_name(value), value)

        Log.log_error(
            f"MapEnum: '{value}' not in map_enum.json, added as {member.name}."
        )
        cls._persist(member.name, value)
        return member

    @classmethod
    def _register_member(cls, name: str, value: str):
        """Dynamically add an enum member for the current process lifetime."""
        if name in cls._member_map_:
            # Name conflict (e.g. inconsistency with older hand-written keys):
            # append a suffix to avoid overwriting
            name = f"{name}__{len(cls._member_map_)}"

        if cls._member_type_ is object:
            member = object.__new__(cls)
        else:  # When EnumBase mixes in str / int / etc.
            member = cls._member_type_.__new__(cls, value)

        member._value_ = value
        member._name_ = name
        member.__objclass__ = cls
        member._sort_order_ = len(cls._member_names_)

        cls._member_names_.append(name)
        cls._member_map_[name] = member
        cls._value2member_map_[value] = member

        try:  # Enable attribute-style access (MapEnum.W1_1) on some Python versions
            type.__setattr__(cls, name, member)
        except Exception:
            pass

        return member

    @classmethod
    def _persist(cls, name: str, value: str):
        """Optional: write the new member to a separate file so that the
        manually maintained map_enum.json is left untouched.
        """
        if AUTO_SAVE_PATH is None:
            return

        try:
            with _lock:
                data = {}
                if AUTO_SAVE_PATH.exists():
                    data = json.loads(AUTO_SAVE_PATH.read_text(encoding="utf-8"))
                data[name] = value
                AUTO_SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
                AUTO_SAVE_PATH.write_text(
                    json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8"
                )
        except Exception as e:
            Log.log_error(f"MapEnum: failed to persist '{value}': {e}")


if not TYPE_CHECKING:
    try:
        data_dict = JsonData.load_json("data|combat|map_enum.json")
    except FileNotFoundError:
        Log.log_error("MapEnum: data/combat/map_enum.json not found.")
        exit(1)

    # Also load any previously auto-saved members
    if AUTO_SAVE_PATH is not None and AUTO_SAVE_PATH.exists():
        try:
            data_dict = {
                **json.loads(AUTO_SAVE_PATH.read_text(encoding="utf-8")),
                **data_dict,
            }
        except Exception as e:
            Log.log_error(f"MapEnum: failed to load {AUTO_SAVE_PATH}: {e}")

    MapEnum = MapEnum("MapEnum", data_dict)  # type: ignore[assignment]
