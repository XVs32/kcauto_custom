import config.config_core as cfg
from fleet.fleet import Fleet
from fleet.noro6 import Noro6
import ships.ships_core as shp
from ships.ship import Ship
from kca_enums.fleet_modes import FleetModeEnum, CombinedFleetModeEnum
from kca_enums.fleet import FleetEnum
from util.kc_time import KCTime
from util.logger import Log
from ships.equipment import Equipment as Equipment
import copy


class FleetCore(object):
    ACTIVE_FLEET_KEY = "active_fleet"
    FleetDict = dict[int, Fleet]
    fleets: dict[str | int, FleetDict | Fleet] = {}

    combined_flag = None

    def __init__(self):

        Log.log_debug_1("FleetCore init.")

        self.fleets[self.ACTIVE_FLEET_KEY] = {}
        self.fleets[self.ACTIVE_FLEET_KEY][1] = Fleet(1, FleetEnum.COMBAT)
        self.fleets[self.ACTIVE_FLEET_KEY][2] = Fleet(2, FleetEnum.EXPEDITION, False)
        self.fleets[self.ACTIVE_FLEET_KEY][3] = Fleet(3, FleetEnum.EXPEDITION, False)
        self.fleets[self.ACTIVE_FLEET_KEY][4] = Fleet(4, FleetEnum.EXPEDITION, False)

    def update_fleets(self, data):

        fleets_in_data = []
        for fleet_data in data:
            fleet_id = fleet_data["api_id"]
            fleets_in_data.append(fleet_id)
            fleet = self.fleets[self.ACTIVE_FLEET_KEY][fleet_id]
            if not fleet.enabled:
                fleet.enabled = True
            if fleet_id == 2:
                fleet.fleet_type = (
                    FleetEnum.COMBAT if self.combined_fleet else FleetEnum.EXPEDITION
                )
            if fleet_id == 3:
                fleet.fleet_type = (
                    FleetEnum.COMBAT
                    if self.strike_force_fleet
                    else FleetEnum.EXPEDITION
                )
            at_base = fleet_data["api_mission"][0] == 0
            if at_base != fleet.at_base:
                fleet.at_base = at_base
            return_time = KCTime.convert_epoch(fleet_data["api_mission"][2])
            if return_time != fleet.return_time:
                fleet.return_time = fleet_data["api_mission"][2]

            fleet.ships = []
            for ship_id in fleet_data["api_ship"]:
                if ship_id != -1:
                    fleet.ships.append(shp.ships.get_ship_from_production_id(ship_id))

        remove_fleets = set(fleets_in_data) - set(
            self.fleets[self.ACTIVE_FLEET_KEY].keys()
        )
        for fleet_id in remove_fleets:
            self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].enabled = False

    @property
    def combat_fleets_id(self):
        if cfg.config.combat.enabled:
            if cfg.config.combat.fleet_mode is FleetModeEnum.STANDARD:
                return [1]
            elif cfg.config.combat.fleet_mode is FleetModeEnum.STRIKE:
                return [3]
            elif CombinedFleetModeEnum.contains_value(
                cfg.config.combat.fleet_mode.value
            ):
                return [1, 2]

    @property
    def combat_fleets(self):
        if cfg.config.combat.enabled:
            if cfg.config.combat.fleet_mode is FleetModeEnum.STANDARD:
                return [self.fleets[self.ACTIVE_FLEET_KEY][1]]
            elif cfg.config.combat.fleet_mode is FleetModeEnum.STRIKE:
                return [self.fleets[self.ACTIVE_FLEET_KEY][3]]
            elif CombinedFleetModeEnum.contains_value(
                cfg.config.combat.fleet_mode.value
            ):
                return [
                    self.fleets[self.ACTIVE_FLEET_KEY][1],
                    self.fleets[self.ACTIVE_FLEET_KEY][2],
                ]
        return []

    @property
    def pvp_fleets(self):
        """method to get the pvp fleet

        Returns:
            List[Fleet]: the pvp fleet if pvp is enabled, List is used to keep consistent with combat_fleets, [] if pvp is not enabled
        """
        if cfg.config.pvp.enabled:
            return [self.fleets[self.ACTIVE_FLEET_KEY][1]]
        return []

    @property
    def combined_fleet(self):
        return len(self.combat_fleets) == 2

    @property
    def strike_force_fleet(self):
        return cfg.config.combat.fleet_mode is FleetModeEnum.STRIKE

    @property
    def ships_in_fleets(self) -> list[Ship]:
        ships = []
        for fleet_id in self.fleets[self.ACTIVE_FLEET_KEY]:
            ships.extend(self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].ships)
        return ships

    @property
    def ships_not_in_fleets(self) -> list[Ship]:

        ships_in_fleets = self.ships_in_fleets

        ship_pool = shp.ships.ship_pool.copy()
        for ship in ships_in_fleets:
            if ship.production_id in ship_pool:
                ship_pool.pop(ship.production_id)
            else:
                Log.log_warn(f"Ship {ship.name} not found in ship pool.")
        return ship_pool.values()

    @property
    def expedition_fleets(self) -> list[Fleet]:
        expedition_fleets = []
        if not cfg.config.expedition.enabled:
            return expedition_fleets

        if (
            len(cfg.config.expedition.fleet_2) > 0
            and self.fleets[self.ACTIVE_FLEET_KEY][2].enabled
        ):
            expedition_fleets.append(self.fleets[self.ACTIVE_FLEET_KEY][2])
        if (
            not self.strike_force_fleet
            and len(cfg.config.expedition.fleet_3) > 0
            and self.fleets[self.ACTIVE_FLEET_KEY][3].enabled
        ):
            expedition_fleets.append(self.fleets[self.ACTIVE_FLEET_KEY][3])
        if (
            len(cfg.config.expedition.fleet_4) > 0
            and self.fleets[self.ACTIVE_FLEET_KEY][4].enabled
        ):
            expedition_fleets.append(self.fleets[self.ACTIVE_FLEET_KEY][4])
        return expedition_fleets

    @property
    def combat_ships(self):
        combat_ships = []
        for f in self.combat_fleets:
            combat_ships += f.ships
        return combat_ships

    @property
    def active_ships(self):
        active_ships = []
        for fleet_id in self.fleets[self.ACTIVE_FLEET_KEY]:
            if self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].enabled:
                active_ships += self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].ships
        return active_ships

    # fleet_id starts form 1
    def get_fleet_id_and_name(self, fleet_id):
        self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].get_fleet_id_and_name()

    def __str__(self):
        for fleet_id in self.fleets[self.ACTIVE_FLEET_KEY]:
            fleet = self.fleets[self.ACTIVE_FLEET_KEY][fleet_id]
            if fleet.enabled:
                Log.log_msg(fleet)

    def materialize_noro6_preset(
        self, noro6: Noro6, preset_name: str
    ) -> dict[int, Fleet]:
        noro6.get_map(preset_name)
        fleet_type = noro6.get_preset_type()
        fleet_count = noro6.get_fleet_count()
        if fleet_count == 0:
            raise ValueError(f"Noro6 preset {preset_name} contains no fleets.")

        fleets = {}

        for fleet_index in range(fleet_count):
            noro6_fleet_id = fleet_index + 1
            noro6.get_fleet(noro6_fleet_id)

            target_fleet = Fleet(
                fleet_index + fleet_type.value,
                fleet_type,
                False,
            )
            target_fleet.ships = []

            for ship_id in range(1, noro6.get_ship_count() + 1):
                noro6_ship = noro6.get_ship(ship_id)
                production_id = noro6_ship["un"]
                active_ship = shp.ships.ship_pool.get(production_id)
                if active_ship is None:
                    raise ValueError(
                        f"Noro6 preset {preset_name} references ship "
                        f"production ID {production_id}, which is not in port."
                    )

                ship = copy.deepcopy(active_ship)
                ship.equipments = []
                empty_normal_slot_seen = False

                for slot_id in range(1, noro6.get_equipment_count() + 1):
                    noro6_equipment = noro6.get_equipment(slot_id)
                    if noro6_equipment["i"] == Equipment.EMPTY_EQUIPMENT:
                        if fleet_type == FleetEnum.COMBAT:
                            Log.log_warn(
                                f"In Noro6 preset {preset_name}, ship {ship.name} has empty equipment slot"
                            )
                        empty_normal_slot_seen = True
                        continue

                    if empty_normal_slot_seen:
                        raise ValueError(
                            f"Noro6 preset {preset_name}, ship {ship.name} "
                            "has equipment after an empty normal slot; "
                            "normal equipment slots must be contiguous."
                        )

                    ship.equipments.append(
                        Equipment(
                            model_id=noro6_equipment["i"],
                            stars=noro6_equipment["r"],
                        )
                    )

                reinforce_equipment = noro6.get_reinforce_equipment()
                if reinforce_equipment["i"] > 0:
                    ship.slot_ex = Equipment(
                        model_id=reinforce_equipment["i"],
                        stars=reinforce_equipment["r"],
                    )
                elif reinforce_equipment["i"] == 0:
                    if active_ship.slot_ex is not None:
                        Log.log_warn(
                            f"Ship {ship.name} has a reinforce slot, but Noro6 config says she doesn't, you might want to update your config."
                        )
                    ship.slot_ex = None
                elif reinforce_equipment["i"] == Equipment.EMPTY_EQUIPMENT:
                    ship.slot_ex = Equipment()
                else:
                    raise ValueError(
                        f"Noro6 preset {preset_name} has unknown reinforcement "
                        f"equipment {reinforce_equipment}."
                    )

                target_fleet.ships.append(ship)

            fleets[noro6_fleet_id] = target_fleet

        return fleets

    def get_noro6_fleet_preset(self, key: str, warn: bool = True):
        noro6 = Noro6()

        for preset in noro6.presets:
            preset_name = preset["name"]
            if preset_name != key:
                continue

            try:
                return self.materialize_noro6_preset(noro6, preset_name)
            except Exception as error:
                if warn:
                    Log.log_error(
                        f"Failed to load Noro6 preset {preset_name}: {error}"
                    )
                return None

        if warn:
            Log.log_error(f"Noro6 preset not found: {key}")
        return None

    def _current_fleet_level_sum(self, fleet_list):
        sum = 0
        for ship in fleet_list:
            sum += ship.level
        return sum

    def get_next_exp_fleet_id(self, fleet_id=-1):

        START_UP = -1

        flag = False
        if fleet_id == START_UP:
            flag = True
        for fleet in self.expedition_fleets:
            if fleet.at_base == False:
                continue
            if fleet.fleet_id == fleet_id:
                flag = True
            elif flag == True:
                return fleet.fleet_id

        Log.log_debug_1(
            f"Failed to get next expedition fleet id, current fleet id: {fleet_id}, return None"
        )
        return None



fleets = FleetCore()
