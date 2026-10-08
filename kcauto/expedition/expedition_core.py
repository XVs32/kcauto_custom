from util.pyvisauto import Region
from random import choice
import copy
import math

from constants import (
    PASSIVE_TIME_INTERVAL,
    OVERNIGHT_TIME_INTERVAL,
    EXPEDITION_DRUM_MODEL_ID,
    EXPEDITION_LANDING_CRAFT_MODEL_ID,
)
import api.api_core as api
import combat.combat_core as com
import config.config_core as cfg
import fleet.fleet_core as flt
from fleet.fleet import Fleet
from fleet.noro6 import Noro6
import random
import resupply.resupply_core as res
import stats.stats_core as sts
import ships.ships_core as shp
import ships.equipment_core as equ
import util.kca as kca_u
from util.timer import Timer
from kca_enums.expeditions import ExpeditionEnum
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.fleet import FleetEnum
from kca_enums.ship_types import ShipTypeEnum
from kca_enums.scroll_directions import ScrollDirectionEnum
from util.core_base import CoreBase
from util.logger import Log
from util.json_data import JsonData
from ships.ship import Ship
from ships.equipment import Equipment


class ExpeditionAssignmentError(Exception):
    pass


class ExpeditionCore(CoreBase):
    MONTHLY_EXPEDITION = [
        ExpeditionEnum.E1_A4,
        ExpeditionEnum.E1_A5,
        ExpeditionEnum.E1_A6,
        ExpeditionEnum.E2_B2,
        ExpeditionEnum.E2_B3,
        ExpeditionEnum.E2_B4,
        ExpeditionEnum.E2_B5,
        ExpeditionEnum.E2_B6,
        ExpeditionEnum.E7_42,
        ExpeditionEnum.E7_43,
        ExpeditionEnum.E7_44,
        ExpeditionEnum.E7_46,
        ExpeditionEnum.E4_D2,
        ExpeditionEnum.E4_D3,
        ExpeditionEnum.E5_E1,
        ExpeditionEnum.E5_E2,
    ]
    EXP_ENUM = "exp_enum"
    SCORE = "score"
    NUM_VISIBLE_EXPEDITONS = 8
    SUPPORT_EXPEDITIONS = [
        ExpeditionEnum.E5_33,
        ExpeditionEnum.E5_34,
        ExpeditionEnum.EE_S1,
        ExpeditionEnum.EE_S2,
    ]
    _available_expeditions = []
    disable_timer = 0
    module_name = "expedition"
    module_display_name = "Expedition"
    available_expeditions_per_world = {}
    exp_state = {}
    exp_data = None
    exp_rank = []
    exp_for_fleet: list[ExpeditionEnum] = []
    TYPE_PRIORITY = [""]
    cur_exp = [
        ExpeditionEnum.NULL,
        ExpeditionEnum.NULL,
        ExpeditionEnum.NULL,
        ExpeditionEnum.NULL,
    ]
    timer = None
    prerequisite_table = {}

    def __init__(self):
        """
        Method to init expedition module
        """
        super().__init__()
        self.timer = Timer()
        self.generated_expedition_fleets = {}
        self.exp_data = JsonData.load_json("data|expedition|expedition.json")
        self.prerequisite_table = JsonData.load_json(
            "data|expedition|expedition_unlock_table.json"
        )

    def get_expedition_static_data(self, exp_enum):
        """read expedition data from json file

        Args:
            id (int): api id of target expedition

        Returns:
            dict: expedition static data, check data|expedition|expedition.json
        """

        for exp in self.exp_data:
            if exp["id"] == exp_enum.value:
                return exp
        return None

    def is_noro6_in_use(self):
        import pvp.pvp_core as pvp

        if com.combat.enabled == True or pvp.pvp.enabled == True:
            return True

        for exp in self.cur_exp:
            if exp == ExpeditionEnum.NULL:
                continue
            if self.is_noro6_exp(exp):
                return True

        return False

    def is_noro6_exp(self, exp_enum):
        return self.get_expedition_static_data(exp_enum) == None

    def is_fleetswitch_needed(self):
        if cfg.config.expedition.fleet_preset == "auto":
            return True
        else:
            return False

    def _build_exp_ship_pool(self):
        exp_ship_pool = {
            ship_type: []
            for ship_type in ShipTypeEnum
            if ship_type != ShipTypeEnum.WILDCARD
        }
        exp_pool = shp.ships.ship_pool.copy()

        for production_id in self._get_noro6_ship_ids():
            exp_pool.pop(production_id, None)

        for ship_id in exp_pool:
            ship = shp.ships.get_ship_from_production_id(ship_id)

            # if this ship is not locked, do not add to exp pool
            if ship.locked == False:
                continue

            exp_ship_pool[ship.ship_type].append(ship)

        for ship_type in exp_ship_pool:
            # sort each ship_type with ammo_max + fuel_max, if ammo_max + fuel_max are the same, sort with level
            exp_ship_pool[ship_type].sort(
                key=lambda x: (x.ammo_max + x.fuel_max, x.level)
            )

        return exp_ship_pool

    def _get_noro6_ship_ids(self):
        noro6 = Noro6()
        ship_ids = set()

        for preset in noro6.presets:
            noro6.get_map(preset["name"])

            for fleet_id in range(1, noro6.get_fleet_count() + 1):
                noro6.get_fleet(fleet_id)

                for ship_id in range(1, noro6.get_ship_count() + 1):
                    ship_ids.add(noro6.get_ship(ship_id)["un"])

        return ship_ids

    def assign_exp_ship(self):
        noro6_available = not self.is_noro6_in_use()
        self.generated_expedition_fleets = {}

        exp_ship_pool = self._build_exp_ship_pool()

        auto_exp_equipment_counts = {
            EXPEDITION_LANDING_CRAFT_MODEL_ID: 0,
            EXPEDITION_DRUM_MODEL_ID: 0,
        }
        for equipment in equ.equipment.equipment_pool[equ.equipment.ID]:
            if equipment.model_id in auto_exp_equipment_counts:
                auto_exp_equipment_counts[equipment.model_id] += 1

        self.exp_for_fleet = [None, None, None, None, None]
        fleet_id = flt.fleets.get_next_exp_fleet_id()

        for i in range(len(self.cur_exp)):
            if self.cur_exp[i] != ExpeditionEnum.NULL:
                for ongoing_ship in flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][
                    i + 1
                ].ships:
                    for standby_ship in exp_ship_pool[ongoing_ship.ship_type][:]:
                        if standby_ship.production_id == ongoing_ship.production_id:
                            exp_ship_pool[ongoing_ship.ship_type].remove(standby_ship)
                            for equipment in ongoing_ship.equipments:
                                if equipment.model_id in auto_exp_equipment_counts:
                                    auto_exp_equipment_counts[equipment.model_id] -= 1

        for exp_in_rank in self.exp_rank:
            exp_static_data = self.get_expedition_static_data(
                ExpeditionEnum(exp_in_rank[self.EXP_ENUM])
            )
            expEnum = exp_in_rank[self.EXP_ENUM]

            if (
                noro6_available
                and flt.fleets.get_noro6_fleet_preset(
                    f"D-{expEnum.expedition}", warn=False
                )
                is not None
            ):
                Log.log_msg(f"Using Noro6 for {expEnum.expedition}.")
                noro6_available = False
                self.exp_for_fleet[fleet_id] = expEnum
                fleet_id = flt.fleets.get_next_exp_fleet_id(fleet_id)

            elif exp_static_data != None:
                exp_ship_requirement = self._get_exp_ship_requirement_from_composition(
                    exp_static_data["reqComposition"]
                )

                try:
                    (
                        assigned_fleet,
                        exp_ship_pool,
                        auto_exp_equipment_counts,
                    ) = self._assign_ship(
                        exp_ship_requirement,
                        exp_ship_pool,
                        auto_exp_equipment_counts,
                        exp_static_data["reqDrum"],
                        exp_static_data["reqDrumCarriers"],
                        4,
                        exp_static_data["reqFlagLevel"],
                        exp_static_data["reqCombinedLevel"],
                    )
                except ExpeditionAssignmentError as error:
                    Log.log_debug_1(str(error))
                    continue

                # Save the fleetShipId
                DEFAULT_FLEET_ID = 1
                self.generated_expedition_fleets[expEnum] = {
                    DEFAULT_FLEET_ID: assigned_fleet
                }
                self.exp_for_fleet[fleet_id] = expEnum

                fleet_id = flt.fleets.get_next_exp_fleet_id(fleet_id)

            if fleet_id == None:
                # assign for all fleets success
                break

        if fleet_id == None:
            # assign for all fleets success
            Log.log_success(
                f"Auto mode assigned ships for expeditions: {[expedition.display_name if expedition != None else None for expedition in self.exp_for_fleet[2:]]}"
            )
            return True
        else:
            # some assign failed
            return False

    def _assign_ship(
        self,
        fleet_list: list[ShipTypeEnum],
        ship_pool: dict[ShipTypeEnum, list[Ship]],
        equipment_counts: dict[int, int],
        req_dc=0,
        req_dc_carrier=0,
        req_lc=4,
        req_lv_flag=0,
        req_lv_sum=0,
    ):
        """
        Method to assign the ship with the given fleet_list and ship_pool

        input:
            fleet_list: The list of ship type (shipTypeEnum)
            ship_pool(dict): The pool of ship to use
                ex. {"DD":[<list of ship() obj>], "CL":[<list of ship() obj>]}
            equipment_counts(dict): Remaining auto-expedition equipment counts by model

        output:
            assigned fleet, remaining ship pool, and remaining equipment counts
        Note:
            This function should handle the wildcard("NA") type,
            so that the output here should not contain any "NA"
        """

        ship_pool = {
            ship_type: ships.copy() for ship_type, ships in ship_pool.items()
        }
        equipment_counts = equipment_counts.copy()

        DRUM_MODELS = [EXPEDITION_DRUM_MODEL_ID]
        LC_MODELS = [EXPEDITION_LANDING_CRAFT_MODEL_ID, 193]

        MORK_FLEET_ID = 2
        assign_fleet = Fleet(MORK_FLEET_ID, FleetEnum.EXPEDITION_PRESET, False)

        flag_ship = True
        pool_level_reverse = False

        for ship_enum in fleet_list:
            if assign_fleet.sum_level < req_lv_sum and pool_level_reverse == False:
                # If the current fleet level sum is less than the required level sum, assign high level ship first
                ship_pool[ship_enum].sort(key=lambda x: x.level, reverse=True)
                pool_level_reverse = True
            elif assign_fleet.sum_level >= req_lv_sum and pool_level_reverse == True:
                ship_pool[ship_enum].sort(key=lambda x: x.level)
                pool_level_reverse = False

            if ship_enum == ShipTypeEnum.NA:
                # @todo: apply the wildcard handling
                ship_enum = ShipTypeEnum.DD

            has_match_ship = False
            ship = None

            for ship in ship_pool[ship_enum]:
                if flag_ship == True and ship.level < req_lv_flag:
                    continue
                # Check if the ship could load LC first
                if req_lc > 0:
                    if len(
                        equ.equipment.is_available_equipments(
                            ship,
                            [Equipment(model_id=model_id) for model_id in LC_MODELS],
                        )
                    ) == len(LC_MODELS):
                        # @todo if the ship is kinu kai 2, she has +1 lc

                        lc_count = min(req_lc, ship.slot_num)

                        temp_ship = copy.deepcopy(ship)
                        assigned_lc_count = min(
                            lc_count,
                            equipment_counts[EXPEDITION_LANDING_CRAFT_MODEL_ID],
                        )
                        temp_ship.equipments = [
                            Equipment(model_id=EXPEDITION_LANDING_CRAFT_MODEL_ID)
                            for _ in range(assigned_lc_count)
                        ]

                        if temp_ship.equipments != []:
                            equipment_counts[EXPEDITION_LANDING_CRAFT_MODEL_ID] -= (
                                assigned_lc_count
                            )
                            req_lc -= assigned_lc_count
                            if temp_ship.slot_ex != None:
                                temp_ship.slot_ex = Equipment()
                            assign_fleet.add_ship(temp_ship)
                            ship_pool[ship_enum].remove(ship)
                            Log.log_debug_1(
                                f"expedition_core: assign ship {ship} for {fleet_list}"
                            )
                            has_match_ship = True
                            break
                        else:
                            raise ExpeditionAssignmentError(
                                f"Failed to assign ships for {fleet_list}: "
                                "insufficient landing craft equipment"
                            )
            if has_match_ship == True:
                continue

            for ship in ship_pool[ship_enum]:
                if flag_ship == True and ship.level < req_lv_flag:
                    continue
                # Check if the ship could load drum, if she can't load LC
                if req_dc > 0 or req_dc_carrier > 0:
                    if len(
                        equ.equipment.is_available_equipments(
                            ship,
                            [Equipment(model_id=model_id) for model_id in DRUM_MODELS],
                        )
                    ) == len(DRUM_MODELS):
                        req_dc_carrier = max(
                            req_dc_carrier, 1
                        )  # make it at least one dc carrier needed, for easier math

                        dc_count = min(req_dc - req_dc_carrier + 1, ship.slot_num)

                        temp_ship = copy.deepcopy(ship)
                        assigned_dc_count = min(
                            dc_count, equipment_counts[EXPEDITION_DRUM_MODEL_ID]
                        )
                        temp_ship.equipments = [
                            Equipment(model_id=EXPEDITION_DRUM_MODEL_ID)
                            for _ in range(assigned_dc_count)
                        ]

                        if temp_ship.equipments != []:
                            equipment_counts[EXPEDITION_DRUM_MODEL_ID] -= (
                                assigned_dc_count
                            )
                            req_dc -= assigned_dc_count
                            req_dc_carrier -= 1
                            if temp_ship.slot_ex != None:
                                temp_ship.slot_ex = Equipment()
                            assign_fleet.add_ship(temp_ship)
                            ship_pool[ship_enum].remove(ship)
                            Log.log_debug_1(
                                f"expedition_core: assign ship {ship} for {fleet_list}"
                            )
                            has_match_ship = True
                            break
                        else:
                            raise ExpeditionAssignmentError(
                                f"Failed to assign ships for {fleet_list}: "
                                "insufficient drum equipment"
                            )
            if has_match_ship == True:
                continue

            # sadly in this case, no ship can load LC or drum, at least now we try to load whatever ship we can find
            for ship in ship_pool[ship_enum]:
                if flag_ship == True and ship.level < req_lv_flag:
                    continue

                temp_ship = copy.deepcopy(ship)
                temp_ship.equipments = []
                if temp_ship.slot_ex != None:
                    temp_ship.slot_ex = Equipment()
                assign_fleet.add_ship(temp_ship)
                ship_pool[ship_enum].remove(ship)
                Log.log_debug_1(
                    f"expedition_core: assign ship {ship} for {fleet_list}"
                )
                has_match_ship = True
                break

            if has_match_ship == False:
                # Cannot find a valid ship
                raise ExpeditionAssignmentError(
                    f"Failed to assign ships for {fleet_list}: "
                    f"no eligible {ship_enum.name} ship available"
                )

            flag_ship = False

        if assign_fleet.sum_level < req_lv_sum:
            raise ExpeditionAssignmentError(
                f"Failed to assign ships for {fleet_list}: "
                f"fleet level sum {assign_fleet.sum_level} is below {req_lv_sum}"
            )

        return assign_fleet, ship_pool, equipment_counts

    def _get_exp_ship_requirement_from_composition(self, composition):
        """
        Convert the string composition (ex. "5DD, 1NA") to
        fleetShipType (ex. [2, 2, 2, 2, 2, 0]
        numbers above is the "stype" of ships (0 for NA is defined by XV, not offical kancolle)
        which is the "api_name" under "api_mst_stype" in kancolle api

        return: list of ShipTypeEnum
        """
        fleetShipType = []

        for type in composition.split(","):
            count = int(type[:1])  # Extract the count from the substring
            item_type = type[1:]  # Extract the type from the substring

            for _ in range(count):
                fleetShipType.append(ShipTypeEnum[item_type])

        return fleetShipType

    def get_prerequisite_expedition(self, exp_enum):
        """
        get the prerequisite expedition of the given expedition

        Args:
            exp_enum(expeditionEnum): current exp
        """
        ret = []
        if str(exp_enum.value) in self.prerequisite_table:
            for prerequisite in self.prerequisite_table[str(exp_enum.value)]:
                ret.append(ExpeditionEnum(prerequisite))
            return ret
        else:
            return [ExpeditionEnum(exp_enum.value - 1)]

    # With a normal function
    def cmp(self, item):
        return item[self.SCORE]

    def get_expedition_ranking(self):

        if (
            ExpeditionEnum.AUTO in cfg.config.expedition.all_expeditions
            or ExpeditionEnum.ACTIVE in cfg.config.expedition.all_expeditions
            or ExpeditionEnum.PASSIVE in cfg.config.expedition.all_expeditions
            or ExpeditionEnum.OVERNIGHT in cfg.config.expedition.all_expeditions
        ):
            pooling_interval = 1

            if ExpeditionEnum.AUTO in cfg.config.expedition.all_expeditions:
                if com.combat.enabled == False:
                    # Passive mode
                    pooling_interval = PASSIVE_TIME_INTERVAL
                else:
                    # Active mode
                    pooling_interval = 1
            elif ExpeditionEnum.ACTIVE in cfg.config.expedition.all_expeditions:
                # Active mode
                pooling_interval = 1
            elif ExpeditionEnum.PASSIVE in cfg.config.expedition.all_expeditions:
                # Passive mode
                pooling_interval = PASSIVE_TIME_INTERVAL
            elif ExpeditionEnum.OVERNIGHT in cfg.config.expedition.all_expeditions:
                # Active mode
                pooling_interval = OVERNIGHT_TIME_INTERVAL

            self.exp_rank = []

            for exp in self.exp_data:
                duration = math.ceil(exp["time"] / pooling_interval) * pooling_interval
                horuly_rsc = {}
                horuly_rsc["fuel"] = exp["fuel"] / duration
                horuly_rsc["ammo"] = exp["ammo"] / duration
                horuly_rsc["steel"] = exp["steel"] / duration
                horuly_rsc["baux"] = exp["baux"] / duration

                def get_item_count(exp, item_name):
                    count = 0
                    if exp.get("item") == item_name:
                        count += exp.get("itemCount", 0)
                    if exp.get("gsItem") == item_name:
                        count += exp.get("gsItemCount", 0)
                    return count

                horuly_rsc["bucket"] = get_item_count(exp, "bucket") / duration
                horuly_rsc["dev_mat"] = get_item_count(exp, "devmat") / duration

                # Check and nullify overflowed resources
                if sts.stats.rsc.fuel >= cfg.config.expedition.desire_oil:
                    horuly_rsc["fuel"] = 0
                if sts.stats.rsc.ammo >= cfg.config.expedition.desire_ammo:
                    horuly_rsc["ammo"] = 0
                if sts.stats.rsc.steel >= cfg.config.expedition.desire_steel:
                    horuly_rsc["steel"] = 0
                if sts.stats.rsc.bauxite >= cfg.config.expedition.desire_bauxite:
                    horuly_rsc["baux"] = 0
                if sts.stats.rsc.bucket >= cfg.config.expedition.desire_bucket:
                    horuly_rsc["bucket"] = 0
                if sts.stats.rsc.dev_mat >= cfg.config.expedition.desire_devmat:
                    horuly_rsc["dev_mat"] = 0

                exp_enum = ExpeditionEnum(exp["id"])

                avg_fill_rate = (
                    (horuly_rsc["fuel"] + sts.stats.rsc.fuel)
                    / cfg.config.expedition.desire_oil
                    + (horuly_rsc["ammo"] + sts.stats.rsc.ammo)
                    / cfg.config.expedition.desire_ammo
                    + (horuly_rsc["steel"] + sts.stats.rsc.steel)
                    / cfg.config.expedition.desire_steel
                    + (horuly_rsc["baux"] + sts.stats.rsc.bauxite)
                    / cfg.config.expedition.desire_bauxite
                    + (horuly_rsc["bucket"] + sts.stats.rsc.bucket)
                    / cfg.config.expedition.desire_bucket
                    + (horuly_rsc["dev_mat"] + sts.stats.rsc.dev_mat)
                    / cfg.config.expedition.desire_devmat
                ) / 6

                balace_score = (
                    abs(
                        (horuly_rsc["fuel"] + sts.stats.rsc.fuel)
                        / cfg.config.expedition.desire_oil
                        - avg_fill_rate
                    )
                    + abs(
                        (horuly_rsc["ammo"] + sts.stats.rsc.ammo)
                        / cfg.config.expedition.desire_ammo
                        - avg_fill_rate
                    )
                    + abs(
                        (horuly_rsc["steel"] + sts.stats.rsc.steel)
                        / cfg.config.expedition.desire_steel
                        - avg_fill_rate
                    )
                    + abs(
                        (horuly_rsc["baux"] + sts.stats.rsc.bauxite)
                        / cfg.config.expedition.desire_bauxite
                        - avg_fill_rate
                    )
                    + abs(
                        (horuly_rsc["bucket"] + sts.stats.rsc.bucket)
                        / cfg.config.expedition.desire_bucket
                        - avg_fill_rate
                    )
                    + abs(
                        (horuly_rsc["dev_mat"] + sts.stats.rsc.dev_mat)
                        / cfg.config.expedition.desire_devmat
                        - avg_fill_rate
                    )
                ) * (-1)

                self.exp_rank.append(
                    {self.EXP_ENUM: exp_enum, self.SCORE: balace_score}
                )
            self.exp_rank.sort(key=self.cmp, reverse=True)

        else:
            self.exp_rank = []

            for exp_enum in cfg.config.expedition.all_expeditions:
                self.exp_rank.append({self.EXP_ENUM: exp_enum, self.SCORE: 0})

    def prerequisite_handling(self):

        NEW = 0
        NOT_CLEARED = 1
        CLEARED = 2

        flag = True
        while flag == True:
            flag = False

            to_remove = set()  # Store IDs of elements to remove

            for exp_rank in self.exp_rank:
                if exp_rank[self.EXP_ENUM] not in self.available_expeditions:
                    Log.log_debug_1(f"expEnum not available {exp_rank}")

                    # Can not use dict in set, use ENUM instead
                    to_remove.add(exp_rank[self.EXP_ENUM])
                    for prerequisite in self.get_prerequisite_expedition(
                        exp_rank[self.EXP_ENUM]
                    ):
                        if prerequisite in self.available_expeditions:
                            if self.exp_state[prerequisite] in {NEW, NOT_CLEARED}:
                                Log.log_debug_1(
                                    f"exp {prerequisite} is in {self.exp_state[prerequisite]} state, adding into prerequisite"
                                )
                                self.exp_rank.append(
                                    {
                                        self.EXP_ENUM: prerequisite,
                                        self.SCORE: exp_rank[self.SCORE],
                                    }
                                )
                            elif self.exp_state[prerequisite] == CLEARED:
                                Log.log_debug_1(
                                    f"exp {prerequisite} cleared already, not adding into prerequisite"
                                )
                            else:
                                Log.log_debug_1(
                                    f"unknown expedition state {self.exp_state[prerequisite]}"
                                )
                                exit(0)
                        else:
                            self.exp_rank.append(
                                {
                                    self.EXP_ENUM: prerequisite,
                                    self.SCORE: exp_rank[self.SCORE],
                                }
                            )
                            Log.log_debug_1(
                                f"exp {prerequisite} is not available, but adding into prerequisite, handle next round"
                            )
                            flag = True

                if flag == True:
                    # run next round immediately
                    break

            self.exp_rank = [
                exp for exp in self.exp_rank if exp[self.EXP_ENUM] not in to_remove
            ]
            self.exp_rank.sort(key=self.cmp, reverse=True)
            # remove duplicate, keep the element with higher score

            seen = set()
            self.exp_rank = [
                exp
                for exp in self.exp_rank
                if exp[self.EXP_ENUM] not in seen and not seen.add(exp[self.EXP_ENUM])
            ]

    def monthly_exp_handling(self):
        """method to remove monthly expedition that already completed this month from expedition ranking"""
        FINISHED = 2
        for exp in self.exp_rank:
            if (
                exp[self.EXP_ENUM] in self.MONTHLY_EXPEDITION
                and self.exp_state[exp[self.EXP_ENUM]] == FINISHED
            ):
                self.exp_rank.remove(exp)

    def on_going_exp_handling(self):
        self.exp_rank = [
            exp
            for exp in self.exp_rank
            if exp[self.EXP_ENUM] not in {on_going_exp for on_going_exp in self.cur_exp}
        ]
        return

    def cut_expedition_queue(self, exp_list):

        remaining_exp_list = exp_list[:]
        new_exp_rank = self.exp_rank[:]

        # cut queue for normal exp first (those exist in exp_rank already)
        for prior_exp in exp_list:
            for exp in self.exp_rank:
                if exp[self.EXP_ENUM] == prior_exp:
                    # Move this exp to first of queue
                    new_exp_rank.remove(exp)
                    new_exp_rank.insert(0, exp)

                    # Prevent index error by checking if there's a second element
                    if len(new_exp_rank) > 1:
                        new_exp_rank[0][self.SCORE] = new_exp_rank[1][self.SCORE] + 1

                    remaining_exp_list.remove(
                        prior_exp
                    )  # Remove safely from a copied list
                    break  # Stop checking further for this `prior_exp`

        # Process remaining expeditions that were not in `self.exp_rank`
        for prior_exp in remaining_exp_list:
            if new_exp_rank:
                new_exp_rank.insert(
                    0,
                    {
                        self.EXP_ENUM: prior_exp,
                        self.SCORE: new_exp_rank[0][self.SCORE] + 1,
                    },
                )

        self.exp_rank = new_exp_rank

    def get_exp_enum_from_name(self, exp_id):
        """
        Args:
            exp_id (int): the name of the expedition

        Returns:
            _type_: the id of the expedition
        """
        for exp in ExpeditionEnum:
            if exp.expedition == exp_id:
                return exp

        Log.log_debug_1(f"Expedition {exp_id} not found")
        return None

    @property
    def available_expeditions(self) -> list[ExpeditionEnum]:
        return self._available_expeditions

    @available_expeditions.setter
    def available_expeditions(self, value):
        available_expeditions = []
        exp_state = {}
        for exped in value:
            exp = ExpeditionEnum(exped["api_mission_id"])
            available_expeditions.append(exp)
            exp_state[exp] = exped["api_state"]

        self._available_expeditions = available_expeditions
        self.exp_state = exp_state

    def populate_available_expeditions_per_world(self):
        self.available_expeditions_per_world = {}
        for expedition in self.available_expeditions:
            world = expedition.world
            if world not in self.available_expeditions_per_world:
                self.available_expeditions_per_world[world] = [expedition]
            else:
                self.available_expeditions_per_world[world].append(expedition)

    def expect_returned_fleets(self):
        returned_fleets = []
        for fleet in flt.fleets.expedition_fleets:
            if fleet.has_returned:
                returned_fleets.append(fleet.fleet_id)

        if len(returned_fleets) == 1:
            Log.log_msg(f"Fleet {returned_fleets[0]} has returned!")
            return True
        elif len(returned_fleets) > 1:
            display_text = kca_u.kca.readable_list_join(returned_fleets)
            Log.log_success(f"Fleets {display_text} have returned!")
            return True
        return False

    @property
    def fleets_are_ready(self):
        if len(self.fleets_to_send) == 1:
            Log.log_msg(
                f"Fleet {self.fleets_to_send[0].fleet_id} ready for expedition."
            )
            return True
        elif len(self.fleets_to_send) > 1:
            display_text = kca_u.kca.readable_list_join(
                [fleet.fleet_id for fleet in self.fleets_to_send]
            )
            Log.log_msg(f"Fleets {display_text} ready for expedition.")
            return True
        return False

    @property
    def fleets_at_base(self) -> list[flt.Fleet]:
        fleets_at_base = []
        for fleet in flt.fleets.expedition_fleets:
            if fleet.at_base:
                fleets_at_base.append(fleet)
        return fleets_at_base

    @property
    def fleets_to_send(self) -> list[flt.Fleet]:
        fleets_to_send = []
        for fleet in self.fleets_at_base:
            fleet_expeditions = cfg.config.expedition.expeditions_for_fleet(
                fleet.fleet_id
            )
            if set(self.SUPPORT_EXPEDITIONS) & set(fleet_expeditions):
                if com.combat.should_and_able_to_sortie():
                    fleets_to_send.append(fleet)
            else:
                fleets_to_send.append(fleet)
        return fleets_to_send

    def send_expeditions(self):
        # @todo: support validate when in auto mode
        self._validate_expeditions()

        for fleet in self.fleets_to_send:
            if any(
                s in cfg.config.expedition.expeditions_for_fleet(fleet.fleet_id)
                for s in (
                    ExpeditionEnum.AUTO,
                    ExpeditionEnum.ACTIVE,
                    ExpeditionEnum.PASSIVE,
                    ExpeditionEnum.OVERNIGHT,
                )
            ):
                expedition = self.exp_for_fleet[fleet.fleet_id]
            else:
                expedition = choice(
                    cfg.config.expedition.expeditions_for_fleet(fleet.fleet_id)
                )

            if expedition not in self.available_expeditions:
                continue

            Log.log_msg(
                f"Sending fleet {fleet.fleet_id} to expedition {expedition.expedition}."
            )
            self._select_world(expedition)
            self._select_expedition(expedition)
            if self._dispatch_expedition(fleet, expedition):
                kca_u.kca.wait("lower", "expedition|expedition_recall.png")
                kca_u.kca.sleep(3)
            else:
                kca_u.kca.click_existing("lower", "expedition|e_world_1.png")
                kca_u.kca.r["top"].hover()

    def _validate_expeditions(self):
        if len(self.available_expeditions) == 0:
            raise ValueError("No list of available expeditions found.")

        all_expedtions = []
        if not any(
            s in cfg.config.expedition.all_expeditions
            for s in (
                ExpeditionEnum.AUTO,
                ExpeditionEnum.ACTIVE,
                ExpeditionEnum.PASSIVE,
                ExpeditionEnum.OVERNIGHT,
            )
        ):
            all_expedtions = cfg.config.expedition.all_expeditions

            for expedition in all_expedtions:
                if expedition not in self.available_expeditions:
                    raise ValueError(
                        f"Specified expedition {expedition.expedition} is not unlocked."
                    )

    def _select_world(self, expedition: ExpeditionEnum):
        kca_u.kca.click_existing("lower", f"expedition|e_world_{expedition.world}.png")

    def _select_expedition(self, expedition: ExpeditionEnum):
        kca_u.kca.sleep(0.1)
        expedition_list = self.available_expeditions_per_world[expedition.world]
        index = expedition_list.index(expedition)
        if index >= self.NUM_VISIBLE_EXPEDITONS:
            self._scroll_list_down()
            offset = len(expedition_list) - self.NUM_VISIBLE_EXPEDITONS
        else:
            self._scroll_list_up()
            offset = 0

        true_index = index - offset
        if not 0 <= true_index < self.NUM_VISIBLE_EXPEDITONS:
            raise ValueError(f"Bad index {true_index}")
        expedition_list_region = Region(
            kca_u.kca.game_x + 190, kca_u.kca.game_y + 244 + (true_index * 45), 520, 35
        )
        kca_u.kca.click(expedition_list_region)
        kca_u.kca.r["top"].hover()
        kca_u.kca.sleep(0.5)

    def _dispatch_expedition(self, fleet: flt.Fleet, expedition: ExpeditionEnum):
        if kca_u.kca.click_existing("lower_right", "global|sortie_select.png"):
            kca_u.kca.sleep(1)  # wait for fleet select panel anime to finish
            fleet.select()
            kca_u.kca.r["top"].hover()

            if fleet.needs_resupply and res.resupply.exp_provisional_enabled in (
                True,
                None,
            ):
                res.resupply.exp_provisional_resupply(fleet)

            if fleet.needs_resupply:
                Log.log_warn(f"Fleet {fleet.fleet_id} needs resupply.")
                return False

            if kca_u.kca.click_existing(
                "lower_right", "expedition|expedition_dispatch.png"
            ):
                result = api.api.update_from_api({KCSAPIEnum.EXPEDITION_START})
                sts.stats.expedition.expeditions_sent += 1
                fleet.at_base = False
                fleet.return_time = result[KCSAPIEnum.EXPEDITION_START.name][0]
                kca_u.kca.r["top"].hover()
                return True
            Log.log_warn(f"Fleet {fleet.fleet_id} is already away.")
            return False
        Log.log_warn(f"Expedition {expedition.expedition} already underway.")
        return False

    def _scroll_list_up(self):
        """Method to scroll the expedition list all the way up."""
        kca_u.kca.scroll(
            "kc", direction=ScrollDirectionEnum.UP, amount=random.randint(10, 15)
        )

    def _scroll_list_down(self):
        """Method to scroll the expedition list all the way down."""
        kca_u.kca.scroll(
            "kc", direction=ScrollDirectionEnum.DOWN, amount=random.randint(10, 15)
        )


expedition = ExpeditionCore()
