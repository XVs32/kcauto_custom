from util.pyvisauto import Region
from sys import exit
from random import choice
from random import randrange

import api.api_core as api
import config.config_core as cfg
import combat.combat_core as com
import pvp.pvp_core as pvp
import repair.repair_core as rep
import expedition.expedition_core as exp
import fleet.fleet_core as flt
import nav.nav as nav
import ship_switcher.ship_switcher_core as ssw
import ships.ships_core as shp
import ships.equipment_core as equ
import util.kca as kca_u
from constants import AUTO_PRESET, OTHER_FLEET_ID
from fleet.fleet import Fleet
from ships.ship import Ship
from kca_enums.fleet_modes import FleetModeEnum
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.ship_types import ShipTypeEnum
from ships.equipment import Equipment
from util.logger import Log


class FleetSwitcherCore(object):
    max_presets = 0
    next_combat_preset = None

    presets = {}
    custom_presets = {}
    exp_fleet_ship_id = {}
    exp_ship_pool = {}
    exp_fleet_ship_type = {}
    equipment_assignments = {}

    def __init__(self):
        self._set_next_combat_preset()

    def update_fleetpreset_data(self, data):
        # print("update_fleetpreset_data")
        self.presets = {}
        self.max_presets = data["api_max_num"]
        for preset_id in data["api_deck"]:
            self.presets[int(preset_id)] = [
                ship_id
                for ship_id in data["api_deck"][preset_id]["api_ship"]
                if ship_id > -1
            ]

    def _set_next_combat_preset(self):
        if len(cfg.config.combat.fleet_presets) > 0:
            self.next_combat_preset = choice(cfg.config.combat.fleet_presets)

    def _get_next_preset_id(self, context):
        preset_id = None
        if context == "combat":
            preset_id = self.next_combat_preset
        elif context == "pvp":
            preset_id = cfg.config.pvp.fleet_preset
        elif context == "factory_develop" or context == "factory_build":
            preset_id = AUTO_PRESET
        elif context == "expedition":
            preset_id = AUTO_PRESET
        return preset_id

    def goto(self):
        ssw.ship_switcher.goto()

    def _find_equipment_row(
        self, equipment_list: list[Equipment], planned_equipment: Equipment
    ):
        for row_idx, equipment in enumerate(equipment_list):
            if (
                equipment.production_id == planned_equipment.production_id
                and equipment.model_id == planned_equipment.model_id
            ):
                return row_idx, equipment

        return -1, planned_equipment

    def _get_equipment_assignment_key(self, ship: Ship, slot):
        return (ship.production_id, slot)

    def _get_planned_equipment(self, ship: Ship, slot):
        key = self._get_equipment_assignment_key(ship, slot)
        return self.equipment_assignments.get(key)

    def _get_ship_active_fleet(self, ship: Ship):
        active_fleets = flt.fleets.fleets.get(flt.fleets.ACTIVE_FLEET_KEY, {})
        for active_fleet in active_fleets.values():
            if ship.production_id in active_fleet.ship_ids:
                return active_fleet
        return None

    def _is_ship_equipment_replaceable(self, ship: Ship):
        if ship.production_id in rep.repair.ships_under_repair:
            return False

        active_fleet = self._get_ship_active_fleet(ship)
        return active_fleet is None or active_fleet.at_base

    def _is_unresolved_noro6_equipment(self, equipment: Equipment):
        return (
            equipment is not None
            and equipment.model_id > 0
            and equipment.production_id == Equipment.UNKNOWN_PRODUCTION_ID
        )

    def _get_target_equipment_conflicts(self, ship: Ship, target_fleet: Fleet):
        target_ship_ids = set(target_fleet.ship_ids)
        target_equipment_ids = {
            equipment.production_id
            for (ship_id, _), equipment in self.equipment_assignments.items()
            if ship_id in target_ship_ids
        }
        conflicts = [
            equipment
            for equipment in ship.equipments
            if equipment.production_id in target_equipment_ids
        ]

        if (
            ship.slot_ex is not None
            and not ship.slot_ex.is_empty_equipment
            and ship.slot_ex.production_id in target_equipment_ids
        ):
            conflicts.append(ship.slot_ex)

        return conflicts

    def _get_protected_ship_ids(self, protected_fleet_ids=None):
        protected_ship_ids = set()
        active_fleets = flt.fleets.fleets.get(flt.fleets.ACTIVE_FLEET_KEY, {})
        for fleet_id in protected_fleet_ids or ():
            protected_fleet = active_fleets.get(fleet_id)
            if protected_fleet is not None:
                protected_ship_ids.update(protected_fleet.ship_ids)
        return protected_ship_ids

    def _get_expedition_protected_fleet_ids(self):
        return {fleet.fleet_id for fleet in flt.fleets.expedition_fleets}

    def _get_safe_free_equipment_refresh_ship(
        self, target_fleet: Fleet, protected_fleet_ids=None, target_ship_ids=None
    ):
        excluded_ship_ids = set(target_ship_ids or ())
        excluded_ship_ids.update(target_fleet.ship_ids)
        excluded_ship_ids.update(self._get_protected_ship_ids(protected_fleet_ids))

        candidates = [
            ship
            for ship in flt.fleets.fleets[flt.fleets.IDLE_FLEET_KEY]
            if ship.production_id not in excluded_ship_ids
            and ship.ship_type != ShipTypeEnum.AR
            and ship.production_id not in rep.repair.ships_under_repair
        ]

        if not candidates:
            Log.log_warn(
                "No safe idle ship found to refresh free equipment list; "
                "continuing without pre-normalize refresh."
            )
            return None

        return candidates[randrange(len(candidates))]

    def _refresh_free_equipment_if_empty(
        self, target_fleet: Fleet, protected_fleet_ids=None, target_ship_ids=None
    ):
        if equ.equipment.equipment_pool.get(equ.equipment.FREE, []):
            return True

        refresh_ship = self._get_safe_free_equipment_refresh_ship(
            target_fleet, protected_fleet_ids, target_ship_ids
        )
        if refresh_ship is None:
            return False

        Log.log_msg(
            f"Free equipment list is empty, use {refresh_ship.name} to update it"
        )
        equ.equipment.goto()
        self.unload_ship(
            refresh_ship,
            idle_ship_list=self._idel_ships_sorted_by_equipment,
            load_random=True,
        )
        return True

    def _is_active_fleet_data_loaded(self):
        active_fleets = flt.fleets.fleets.get(flt.fleets.ACTIVE_FLEET_KEY, {})
        fleet_1 = active_fleets.get(1)
        return bool(shp.ships.ship_pool and fleet_1 is not None and fleet_1.ships)

    def _get_movable_equipment_pool(self, protected_fleet_ids=None):
        protected_fleet_ids = set(protected_fleet_ids or ())
        equipment_by_id = {}
        equipment_sources = {}

        def add_equipment(equipment, source_ship=None, slot=None):
            if (
                equipment is None
                or equipment.model_id <= 0
                or equipment.production_id <= 0
            ):
                return

            if equipment.production_id not in equipment_by_id:
                equipment_by_id[equipment.production_id] = equipment
                equipment_sources[equipment.production_id] = (source_ship, slot)

        for equipment in equ.equipment.equipment_pool.get(equ.equipment.FREE, []):
            add_equipment(equipment)

        candidate_ship_ids = set()

        def add_ship(ship: Ship):
            if ship.production_id in candidate_ship_ids:
                return
            if not self._is_ship_equipment_replaceable(ship):
                return

            candidate_ship_ids.add(ship.production_id)
            for slot, equipment in enumerate(ship.equipments):
                add_equipment(equipment, ship, slot)
            add_equipment(ship.slot_ex, ship, "slot_ex")

        for ship in flt.fleets.ships_not_in_fleets:
            add_ship(ship)

        if self._is_active_fleet_data_loaded():
            active_fleets = flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY]
            for fleet_id, active_fleet in active_fleets.items():
                if fleet_id in protected_fleet_ids or not active_fleet.at_base:
                    continue

                for ship in active_fleet.ships:
                    add_ship(ship)
        else:
            Log.log_warn(
                "Active fleet data is not loaded; limiting equipment allocation "
                "to free equipment and idle ships."
            )

        return equipment_by_id, equipment_sources

    def _collect_target_equipment_slots(self, target_fleets: list[Fleet]):
        target_slots = []
        target_ship_ids = set()

        for target_fleet in target_fleets:
            for target_ship in target_fleet.ships:
                if target_ship.production_id in target_ship_ids:
                    Log.log_error(
                        f"Ship {target_ship.production_id}/{target_ship.name_jp} "
                        "is assigned to more than one target fleet."
                    )
                    return None

                target_ship_ids.add(target_ship.production_id)

                for slot, target_equipment in enumerate(target_ship.equipments):
                    if target_equipment.model_id > 0:
                        target_slots.append((target_ship, slot, target_equipment))

                if target_ship.slot_ex is not None and target_ship.slot_ex.model_id > 0:
                    target_slots.append((target_ship, "slot_ex", target_ship.slot_ex))

        return target_slots

    def _get_equipment_allocation_priority(
        self,
        target_equipment: Equipment,
        equipment: Equipment,
        equipment_sources,
    ):
        source_ship, _ = equipment_sources.get(
            equipment.production_id, (None, None)
        )
        source_priority = 0 if source_ship is None else 1

        return (
            source_priority,
            abs(equipment.stars - target_equipment.stars),
            equipment.production_id,
        )

    def _plan_equipment_assignments(
        self, target_fleets: list[Fleet], protected_fleet_ids=None
    ):
        self.equipment_assignments = {}

        target_slots = self._collect_target_equipment_slots(target_fleets)
        if target_slots is None:
            return False

        equipment_by_id, equipment_sources = self._get_movable_equipment_pool(
            protected_fleet_ids
        )
        assigned_equipment_ids = set()
        assignments = {}

        # Reserve every available exact production ID before using any same-model
        # replacement. This keeps one target slot from consuming equipment that
        # another target slot explicitly requested.
        for target_ship, slot, target_equipment in target_slots:
            if self._is_unresolved_noro6_equipment(target_equipment):
                continue

            exact_equipment = equipment_by_id.get(target_equipment.production_id)
            if (
                exact_equipment is not None
                and exact_equipment.model_id == target_equipment.model_id
                and exact_equipment.production_id not in assigned_equipment_ids
            ):
                key = self._get_equipment_assignment_key(target_ship, slot)
                assignments[key] = exact_equipment
                assigned_equipment_ids.add(exact_equipment.production_id)

        # Preserve already-loaded same-model equipment for flexible targets before
        # choosing new replacements. Exact production ID reservations above still
        # take precedence over keeping equipment in place.
        for target_ship, slot, target_equipment in target_slots:
            key = self._get_equipment_assignment_key(target_ship, slot)
            if key in assignments:
                continue

            active_ship = shp.ships.ship_pool.get(target_ship.production_id)
            if active_ship is None:
                continue

            if slot == "slot_ex":
                current_equipment = active_ship.slot_ex
            elif slot < len(active_ship.equipments):
                current_equipment = active_ship.equipments[slot]
            else:
                current_equipment = None

            if (
                current_equipment is not None
                and current_equipment.model_id == target_equipment.model_id
                and current_equipment.production_id in equipment_by_id
                and current_equipment.production_id not in assigned_equipment_ids
            ):
                assignments[key] = current_equipment
                assigned_equipment_ids.add(current_equipment.production_id)

        # Remaining slots prefer free equipment before equipment mounted on another
        # movable ship, then use stars and production ID as stable tie-breakers.
        for target_ship, slot, target_equipment in target_slots:
            key = self._get_equipment_assignment_key(target_ship, slot)
            if key in assignments:
                continue

            candidates = [
                equipment
                for equipment in equipment_by_id.values()
                if equipment.model_id == target_equipment.model_id
                and equipment.production_id not in assigned_equipment_ids
            ]
            slot_name = "slot_ex" if slot == "slot_ex" else f"slot {slot + 1}"
            target_id = (
                f"model {target_equipment.model_id}"
                if self._is_unresolved_noro6_equipment(target_equipment)
                else str(target_equipment.production_id)
            )
            if not candidates:
                Log.log_error(
                    f"Cannot find replacement for "
                    f"{target_equipment.name} {target_equipment.stars}★ ({target_id}) "
                    f"on {target_ship.name_jp} {slot_name}."
                )
                return False

            selected_equipment = min(
                candidates,
                key=lambda equipment: self._get_equipment_allocation_priority(
                    target_equipment,
                    equipment,
                    equipment_sources,
                ),
            )
            assignments[key] = selected_equipment
            assigned_equipment_ids.add(selected_equipment.production_id)

        for target_ship, slot, target_equipment in target_slots:
            key = self._get_equipment_assignment_key(target_ship, slot)
            selected_equipment = assignments[key]

            if (
                not self._is_unresolved_noro6_equipment(target_equipment)
                and selected_equipment.production_id == target_equipment.production_id
            ):
                continue

            slot_name = "slot_ex" if slot == "slot_ex" else f"slot {slot + 1}"
            target_id = (
                f"model {target_equipment.model_id}"
                if self._is_unresolved_noro6_equipment(target_equipment)
                else str(target_equipment.production_id)
            )
            Log.log_warn(
                f"Using {selected_equipment.name} {selected_equipment.stars}★ "
                f"({selected_equipment.production_id}) instead of "
                f"{target_equipment.name} {target_equipment.stars}★ "
                f"({target_id}) for {target_ship.name_jp} {slot_name}."
            )

        self.equipment_assignments = assignments
        return True

    def _prepare_equipment_plan(
        self,
        target_fleets: list[Fleet],
        protected_fleet_ids=None,
        target_ship_ids=None,
    ):
        self.equipment_assignments = {}
        if not target_fleets:
            return True

        if target_ship_ids is None:
            target_ship_ids = {
                ship.production_id
                for target_fleet in target_fleets
                for ship in target_fleet.ships
            }

        if not self._refresh_free_equipment_if_empty(
            target_fleets[0], protected_fleet_ids, target_ship_ids
        ):
            return False

        return self._plan_equipment_assignments(target_fleets, protected_fleet_ids)

    def _is_ship_equipment_assignment_matched(
        self, active_ship: Ship, target_ship: Ship
    ):
        slot_count = max(
            active_ship.slot_num,
            target_ship.slot_num,
            len(active_ship.equipments),
            len(target_ship.equipments),
        )

        for slot in range(slot_count):
            active_equipment = (
                active_ship.equipments[slot]
                if slot < len(active_ship.equipments)
                else None
            )
            target_equipment = (
                target_ship.equipments[slot]
                if slot < len(target_ship.equipments)
                else None
            )

            if target_equipment is None or target_equipment.model_id <= 0:
                if active_equipment is not None and active_equipment.model_id > 0:
                    return False
                continue

            planned_equipment = self._get_planned_equipment(target_ship, slot)
            if (
                planned_equipment is None
                or active_equipment is None
                or active_equipment.production_id != planned_equipment.production_id
            ):
                return False

        active_slot_ex = (
            active_ship.slot_ex
            if active_ship.slot_ex is not None
            and not active_ship.slot_ex.is_empty_equipment
            else None
        )
        target_slot_ex = (
            target_ship.slot_ex
            if target_ship.slot_ex is not None
            and not target_ship.slot_ex.is_empty_equipment
            else None
        )

        if target_slot_ex is None:
            return active_slot_ex is None

        planned_slot_ex = self._get_planned_equipment(target_ship, "slot_ex")
        return (
            planned_slot_ex is not None
            and active_slot_ex is not None
            and active_slot_ex.production_id == planned_slot_ex.production_id
        )

    def _is_custom_fleet_with_equipment_loaded(self, fleet_id, target_fleet: Fleet):
        active_fleet = flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id]

        if active_fleet.ship_ids != target_fleet.ship_ids:
            return False

        for i in range(target_fleet.size):
            active_ship = active_fleet.ships[i]
            target_ship = target_fleet.ships[i]

            if not self._is_ship_equipment_assignment_matched(active_ship, target_ship):
                return False

        return True

    def switch_fleet(self, context):
        self.goto()
        preset_id = self._get_next_preset_id(context)

        if preset_id == AUTO_PRESET:
            if context == "combat":
                Log.log_msg(
                    f"Switching to Fleet Preset for {cfg.config.combat.sortie_map.display_name}."
                )

                fleet_list = self._get_fleet_preset(cfg.config.combat.sortie_map.value)

                # Avoiding load process of fleet 2, 3 messing up fleet 1
                # Combat is a property, sort does not saved inside it
                rev_fleet_id = flt.fleets.combat_fleets_id.copy()
                rev_fleet_id.sort(reverse=True)
                protected_fleet_ids = self._get_expedition_protected_fleet_ids()
                target_ship_ids = set()
                combat_targets = []

                for combat_fleet_id in rev_fleet_id:
                    target_fleet_id = 1 if combat_fleet_id == 3 else combat_fleet_id
                    target_fleet = fleet_list[target_fleet_id]
                    combat_targets.append((combat_fleet_id, target_fleet))
                    target_ship_ids.update(target_fleet.ship_ids)

                if not self._prepare_equipment_plan(
                    [target_fleet for _, target_fleet in combat_targets],
                    protected_fleet_ids,
                    target_ship_ids,
                ):
                    return False

                for combat_fleet_id, target_fleet in combat_targets:
                    if not self.switch_to_costom_fleet_with_equipment(
                        combat_fleet_id,
                        target_fleet,
                        protected_fleet_ids,
                        target_ship_ids,
                        equipment_plan_ready=True,
                    ):
                        return False

                    protected_fleet_ids.add(combat_fleet_id)

                nav.navigate.to("refresh_home")

                if cfg.config.combat.fleet_mode != flt.fleets.combined_flag:
                    nav.navigate.to("fleetcomp")
                    if (
                        flt.fleets.combined_flag == FleetModeEnum.CTF
                        or flt.fleets.combined_flag == FleetModeEnum.STF
                        or flt.fleets.combined_flag == FleetModeEnum.TCF
                    ):
                        kca_u.kca.click_existing(
                            "upper_left", f"fleet|combine_cancel.png"
                        )

                    if (
                        cfg.config.combat.fleet_mode == FleetModeEnum.CTF
                        or cfg.config.combat.fleet_mode == FleetModeEnum.STF
                        or cfg.config.combat.fleet_mode == FleetModeEnum.TCF
                    ):
                        Log.log_msg(
                            f"Switching to {cfg.config.combat.fleet_mode.display_name} mode."
                        )

                        # merge fleet #2 to fleet #1
                        flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][2].select()
                        start_region = kca_u.kca.find(
                            "top_submenu", f"fleet|fleet_2_active.png"
                        )
                        end_region = kca_u.kca.find("top_submenu", f"fleet|fleet_1.png")
                        kca_u.kca.drag(start_region, end_region)

                        if cfg.config.combat.fleet_mode == FleetModeEnum.CTF:
                            kca_u.kca.click_existing("center", f"fleet|ctf.png")
                        elif cfg.config.combat.fleet_mode == FleetModeEnum.STF:
                            kca_u.kca.click_existing("center", f"fleet|stf.png")
                        elif cfg.config.combat.fleet_mode == FleetModeEnum.TCF:
                            kca_u.kca.click_existing("center", f"fleet|tcf.png")

                        kca_u.kca.click_existing("lower", f"fleet|combine_fleet.png")

                """Check if next combat possible, since new ship is switched in"""
                """Refresh home to update ship list"""
                com.combat.set_next_sortie_time(override=True)

            elif context == "pvp":
                Log.log_msg(f"Switching to PvP Preset.")

                fleet_list = self._get_fleet_preset(
                    pvp.pvp.next_pvp_quest.name + "-pvp"
                )

                protected_fleet_ids = self._get_expedition_protected_fleet_ids()
                if not self.switch_to_costom_fleet_with_equipment(
                    1, fleet_list[1], protected_fleet_ids
                ):
                    return False

            elif context == "expedition":
                Log.log_msg(f"Switching to Exp Preset.")

                protected_fleet_ids = set()
                expedition_targets = []
                target_ship_ids = set()
                fleet_id = flt.fleets.get_next_exp_fleet_id()

                while (
                    fleet_id != None and exp.expedition.exp_for_fleet[fleet_id] != None
                ):
                    DEFAULT_FLEET_ID = 1
                    target_fleet = self._get_fleet_preset(
                        exp.expedition.exp_for_fleet[fleet_id]
                    )[DEFAULT_FLEET_ID]
                    expedition_targets.append((fleet_id, target_fleet))
                    target_ship_ids.update(target_fleet.ship_ids)
                    fleet_id = flt.fleets.get_next_exp_fleet_id(fleet_id)

                if expedition_targets and not self._prepare_equipment_plan(
                    [target_fleet for _, target_fleet in expedition_targets],
                    protected_fleet_ids,
                    target_ship_ids,
                ):
                    return False

                for fleet_id, target_fleet in expedition_targets:
                    if not self.switch_to_costom_fleet_with_equipment(
                        fleet_id,
                        target_fleet,
                        protected_fleet_ids,
                        target_ship_ids,
                        equipment_plan_ready=True,
                    ):
                        return False
                    protected_fleet_ids.add(fleet_id)

            elif context == "factory_develop":
                develop_sec = cfg.config.factory.develop_secretary
                if isinstance(develop_sec, ShipTypeEnum):
                    ship = shp.ships.get_highest_level_ship_by_type(develop_sec)
                    if ship is None:
                        return False
                    Log.log_msg(
                        f"Switching to highest level {develop_sec.display_name} "
                        f"({ship.name_jp}) for develop."
                    )
                else:
                    ship = shp.ships.get_ship_from_production_id(develop_sec)
                    if ship is None:
                        return False

                    Log.log_msg(f"Switching to {ship.name_jp} for develop.")
                ssw.ship_switcher.current_page = 1
                ssw.ship_switcher.switch_slot(1, ship)
            elif context == "factory_build":
                build_sec = cfg.config.factory.build_secretary
                if isinstance(build_sec, ShipTypeEnum):
                    ship = shp.ships.get_highest_level_ship_by_type(build_sec)
                    if ship is None:
                        return False
                    Log.log_msg(
                        f"Switching to highest level {build_sec.display_name} "
                        f"({ship.name_jp}) for construction."
                    )
                else:
                    ship = shp.ships.get_ship_from_production_id(build_sec)
                    if ship is None:
                        return False

                    Log.log_msg(f"Switching to {ship.name_jp} for construction.")
                ssw.ship_switcher.current_page = 1
                ssw.ship_switcher.switch_slot(1, ship)
        elif preset_id == None:
            Log.log_debug_1(f"Fleet switch disabled.")
        else:
            Log.log_msg(f"Switching to Fleet Preset {preset_id}.")
            if preset_id not in self.presets:
                Log.log_error(
                    f"Fleet Preset {preset_id} is not specified in-game. Please "
                    f"check your config."
                )
                exit(1)

            """open preset menu"""
            kca_u.kca.click_existing(
                "lower_left", "fleetswitcher|fleetswitch_submenu.png"
            )
            kca_u.kca.wait("lower_left", "fleetswitcher|fleetswitch_submenu_exit.png")

            list_idx = (preset_id if preset_id < 5 else 5) - 1
            idx_offset = preset_id - 5
            if idx_offset > 0:
                self._scroll_preset_list(idx_offset)

            kca_u.kca.r["top"].hover()
            preset_idx_region = Region(
                kca_u.kca.game_x + 410, kca_u.kca.game_y + 275 + (list_idx * 76), 70, 45
            )
            kca_u.kca.click_existing(
                preset_idx_region, "fleetswitcher|fleetswitch_button.png"
            )
            if kca_u.kca.exists("left", "fleetswitcher|fleetswitch_fail_check.png"):
                Log.log_error(
                    f"Could not switch in fleet preset {preset_id}. Please check "
                    f"your config and fleet presets."
                )
                exit(1)
            Log.log_msg(f"Fleet Preset {preset_id} loaded.")

            if context == "combat":
                self._set_next_combat_preset()
        return True

    def switch_to_costom_fleet(self, fleet_id, costom_fleet: Fleet):
        """
        method to switch the ship in {fleet_id} to ships defined in {ship_list}

        fleet_id(int): fleet to switch, index starts from 1
        ship_list(fleetcore_obj): ships to use
        """

        retry = 0

        while True:
            flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].select()

            empty_slot_count = 0

            size = max(
                flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].size,
                costom_fleet.size,
            )

            STRIKE_FLEET_SIZE = 7
            NORMAL_FLEET_SIZE = 6
            if size > STRIKE_FLEET_SIZE:
                Log.log_warn(
                    f"kcauto tries to switch to fleet with size {size}, this may cause unexpected behavior."
                )

            if fleet_id == 3:
                size = min(STRIKE_FLEET_SIZE, size)
            else:
                size = min(NORMAL_FLEET_SIZE, size)

            any_vaild_switch = False
            retry = False
            for i in range(1, size + 1):
                if i > costom_fleet.size:
                    ship = None
                else:
                    ship = shp.ships.get_ship_from_production_id(
                        costom_fleet.ship_ids[i - 1]
                    )
                    if ship is None:
                        return False

                if i <= len(
                    flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids
                ) and shp.ships.is_same_ship(
                    ship,
                    flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ships[
                        i - 1
                    ],
                ):
                    Log.log_debug_1("Ship already loaded for custom fleet.")
                    continue

                if not ssw.ship_switcher.switch_slot(i - empty_slot_count, ship):
                    # fleet data update
                    if any_vaild_switch == True:
                        Log.log_msg(f"Retrying...")
                        nav.navigate.to("home")
                        self.goto()
                        retry = True
                        break
                    else:
                        return False

                else:
                    any_vaild_switch = True

                if ship == None:
                    empty_slot_count += 1

            if retry == True:
                continue
            else:
                break

        Log.log_success("Fleet load complete.")
        return True

    def switch_to_costom_fleet_with_equipment(
        self,
        fleet_id,
        costom_fleet: Fleet,
        protected_fleet_ids=None,
        target_ship_ids=None,
        equipment_plan_ready=False,
    ):
        """
        method to switch the ship in {fleet_id} to ships defined in {ship_list}

        fleet_id(int): fleet to switch, index starts from 1
        custom_fleet(Fleet): Fleet obj contain ships to use
        """

        if not equipment_plan_ready and not self._prepare_equipment_plan(
            [costom_fleet], protected_fleet_ids, target_ship_ids
        ):
            return False

        if self._is_custom_fleet_with_equipment_loaded(fleet_id, costom_fleet):
            Log.log_msg(f"Fleet {fleet_id} ships and equipment are already loaded")
            return True

        self._unload_fleet_required_equipment(
            costom_fleet, protected_fleet_ids, target_ship_ids
        )

        Log.log_success("Equipment unloaded.")

        nav.navigate.to("home")

        self.goto()

        self.switch_to_costom_fleet(fleet_id, costom_fleet)

        self._load_equipment(fleet_id, costom_fleet)
        Log.log_success("Equipment loaded.")

        return True

    def _scroll_preset_list(self, target_clicks):
        Log.log_debug_1(f"Scrolling to target preset ({target_clicks} clicks).")
        clicks = 0
        while clicks < target_clicks:
            kca_u.kca.click_existing("lower_left", "global|scroll_next.png")
            clicks += 1

    def _get_fleet_preset(self, key):
        """
        method to get the preset for combat or expedition
        input:
            key(string): the name of combat map(ex. Bm2-1-1)
        """
        if key in flt.fleets.fleets:
            return flt.fleets.fleets[key]
        else:
            if key[0] == "B" or key[0] == "C":
                quest_end = key.find("-")

                Log.log_warn(
                    f"Preset {str(key)} not found, use default {key[0] + key[quest_end:]}"
                )
                key = key[0] + key[quest_end:]
            else:
                Log.log_error("Unexpected preset id:" + str(key))
            return flt.fleets.fleets[key]

    @property
    def _idel_ships_sorted_by_equipment(self):
        temp_list = sorted(
            flt.fleets.ships_not_in_fleets,
            key=lambda item: (item.sort_id, item.production_id),
        )
        temp_list = sorted(temp_list, key=lambda s: s.level, reverse=True)

        temp_list.reverse()

        return temp_list

    def _unload_fleet_required_equipment(
        self, target_fleet: Fleet, protected_fleet_ids=None, target_ship_ids=None
    ):
        """
        method to unload the equipments used by this fleet
        """

        any_unload = False

        nav.navigate.to("refresh_home")

        unload_ships: list[Ship] = []
        protected_ship_ids = self._get_protected_ship_ids(protected_fleet_ids)
        needed_load = False
        for production_id in shp.ships.ship_pool:
            ship = shp.ships.ship_pool[production_id]
            if ship.production_id in target_fleet.ship_ids:
                target_ship = target_fleet.get_ship_by_production_id(ship.production_id)

                if not self._is_ship_equipment_assignment_matched(ship, target_ship):
                    needed_load = True

                    if ship.slot_ex != None and target_ship.slot_ex == None:
                        Log.log_warn(
                            f"Ship {ship.name} has a reinforce slot, but Noro6 config says she doesn't, you might want to update your config."
                        )

                    if (
                        ship.has_equipment() == True
                        and self._is_ship_equipment_replaceable(ship)
                        and ship.production_id not in protected_ship_ids
                    ):
                        unload_ships.append(ship)
                        any_unload = True
            else:  # target_config does not care this ship, but we still have to strip it if it holds any equipment we care
                conflicts = self._get_target_equipment_conflicts(ship, target_fleet)
                if conflicts:
                    if (
                        ship.production_id in protected_ship_ids
                        or not self._is_ship_equipment_replaceable(ship)
                    ):
                        continue

                    unload_ships.append(ship)
                    any_unload = True

        if any_unload == False and needed_load == True:
            # let a safe idle ship load and unload a whatever equipment
            refresh_ship = self._get_safe_free_equipment_refresh_ship(
                target_fleet, protected_fleet_ids, target_ship_ids
            )
            if refresh_ship is None:
                return False

            unload_ships = [refresh_ship]

        elif any_unload == False and needed_load == False:
            Log.log_msg(f"No equipment to unload or load")
            return False

        load_random = any_unload == False and needed_load == True

        equ.equipment.goto()

        idle_ship_list = self._idel_ships_sorted_by_equipment
        for ship in unload_ships:
            conflicts = self._get_target_equipment_conflicts(ship, target_fleet)

            if load_random:
                Log.log_msg(
                    f"Use {ship.production_id}/{ship.name} to update equipment list"
                )
            elif conflicts:
                conflict_text = ", ".join(
                    f"{equipment.name} ({equipment.production_id})"
                    for equipment in conflicts
                )
                Log.log_msg(
                    f"Need to unload equipment for "
                    f"{ship.production_id}/{ship.name}: {conflict_text}"
                )
            else:
                Log.log_msg(
                    f"Need to unload equipment for {ship.production_id}/{ship.name}"
                )

            self.unload_ship(
                ship,
                idle_ship_list=idle_ship_list,
                load_random=load_random,
            )

        return any_unload

    def unload_ship(
        self, ship: Ship, idle_ship_list: list[Ship] = None, load_random=False
    ):
        """
        unload a ship in the specified fleet, assume nav in equipment page already
        input:
            fleet_id: int, starts from 1
            ship_id: int, ship production id
        """

        ships_to_check = idle_ship_list

        if ships_to_check == None:
            ships_to_check = self._idel_ships_sorted_by_equipment

        target_fleet = OTHER_FLEET_ID

        for fleet_id in flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY]:
            if (
                ship.production_id
                in flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids
            ):
                target_fleet = fleet_id
                break

        equ.equipment.goto_fleet(target_fleet)

        if target_fleet == OTHER_FLEET_ID:
            Log.log_msg(f"Ship {ship.name} is not in any fleet, unload from idle fleet")
            for k, idle_ship in enumerate(ships_to_check):
                if shp.ships.is_same_ship(ship, idle_ship):
                    idx = k
                    break
            ssw.ship_switcher.select_replacement_row(
                row_idx=idx, ship=ship, mode=ssw.ship_switcher.EQUIPMENT_SHIP_MODE
            )

        else:
            Log.log_debug_1(
                f"Ship {ship.name} is in fleet {fleet_id}, unload from there"
            )
            ship_position = flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][
                fleet_id
            ].ship_ids.index(ship.production_id)

            click_ship_in_equipment_page(ship_position)

        if load_random == True:
            # unload a ship to update equipment list
            kca_u.kca.click("1_slot_equipment")

            ssw.ship_switcher.select_replacement_row(
                row_idx=randrange(10), mode=ssw.ship_switcher.EQUIPMENT_MODE
            )

            kca_u.kca.click_existing(
                "lower_right", "shipswitcher|shiplist_shipswitch_button.png"
            )
            kca_u.kca.wait("lower", "shipswitcher|equipment_panel.png")
            api_result = api.api.update_from_api(
                {KCSAPIEnum.FREE_EQUIPMENT}, process_all=True
            )

        if ship.slot_num == 1:
            Log.log_debug_1(f"1 slot ship")
            kca_u.kca.click("1_slot_unload_equipment")
        elif ship.slot_num == 2:
            Log.log_debug_1(f"2 slot ship")
            kca_u.kca.click("2_slot_unload_equipment")
        elif ship.slot_num == 3:
            Log.log_debug_1(f"3 slot ship")
            kca_u.kca.click("3_slot_unload_equipment")
        elif ship.slot_num == 4:
            Log.log_debug_1(f"4 slot ship")
            kca_u.kca.click("4_slot_unload_equipment")
        elif ship.slot_num == 5:
            Log.log_debug_1(f"5 slot ship")
            kca_u.kca.click("5_slot_unload_equipment")
        else:
            Log.log_warn(f"Unexpected slot number {ship.slot_num}, exiting...")
            exit(1)

        kca_u.kca.wait("lower", "shipswitcher|equipment_panel.png")

        if ship.slot_ex != None and ship.slot_ex.is_empty_equipment == False:
            Log.log_debug_1(f"reinforce slot ship, slot_ex = {ship.slot_ex.name}")
            kca_u.kca.click("reinforce_slot_unload_equipment")

        kca_u.kca.wait("lower", "shipswitcher|equipment_panel.png")

        api_result = api.api.update_from_api(
            {KCSAPIEnum.FREE_EQUIPMENT}, process_all=True
        )
        if api_result == {}:
            Log.log_error(f"Something went wrong, skipping this round...")
            exit(1)

            retry = 10
            while not kca_u.kca.exists("left", "nav|side_menu_home.png"):
                kca_u.kca.click_existing(
                    "bottom_right",
                    "shipswitcher|equipment_cancel_reinforce.png",
                    cached=True,
                )

                if retry > 0:
                    retry -= 1
                    kca_u.sleep(1)
                else:
                    Log.log_error(f"kcauto cannot figure out where it is, exiting...")
                    exit()
            # skiping unload for this ship  <= usually it is already unloaded, but api didn't update due to network delay

        return True

    def _load_equipment(self, fleet_id, fleet: Fleet):

        nav.navigate.to("home")

        load_ship_id = fleet.ship_ids

        if (
            flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids
            != fleet.ship_ids
        ):
            Log.log_error(
                f"Fleet {fleet_id} ship IDs do not match; ship load may have failed, exiting..."
            )
            exit(1)
        elif (
            flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].under_repair
            == True
        ):
            Log.log_error(
                f"Fleet {fleet_id} is under repair; equipment load process halted."
            )
            return

        needed_load = False
        for i in range(fleet.size):
            if not self._is_ship_equipment_assignment_matched(
                flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ships[i],
                fleet.ships[i],
            ):
                needed_load = True
                break

        if needed_load == False:
            Log.log_msg(f"equipment for fleet {fleet_id} is already loaded")
            return False
        else:
            equ.equipment.goto()
            equ.equipment.goto_fleet(fleet_id)

        for i in range(fleet.size):
            if self._is_ship_equipment_assignment_matched(
                flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ships[i],
                fleet.ships[i],
            ):
                Log.log_msg(f"equipment for {fleet.ships[i].name_jp} is already loaded")
                continue
            else:
                Log.log_msg(f"Loading equipment for {fleet.ships[i].name_jp}...")

            click_ship_in_equipment_page(i)

            first_load = True
            ssw.ship_switcher.current_page = 1

            available_equipment_list = fleet.ships[i].available_equipments

            for k, equipment in enumerate(available_equipment_list):
                if k % 10 == 0:
                    Log.log_debug_1(f"Page {k // 10 + 1}")
                Log.log_debug_1(
                    f"{k}: {equipment.name} {equipment.stars} (Production id: {equipment.production_id}, Model id: {equipment.model_id}), category id: {equipment.category}"
                )

            for slot in range(fleet.ships[i].equipment_count):
                kca_u.kca.click(str(slot + 1) + "_slot_equipment")

                if first_load == True:
                    kca_u.kca.click_existing(
                        "upper_right", "shipswitcher|equipment_sort_arrow.png"
                    )
                    kca_u.kca.click("equipment_sort_all")
                    first_load = False

                    kca_u.kca.wait("upper_right", "shipswitcher|equipment_sort_all.png")

                planned_equipment = self._get_planned_equipment(
                    fleet.ships[i], slot
                )
                if planned_equipment is None:
                    Log.log_error(
                        f"No planned equipment assignment for "
                        f"{fleet.ships[i].name_jp} slot {slot + 1}."
                    )
                    exit(1)

                row_idx, selected_equipment = self._find_equipment_row(
                    equ.equipment.equipment_pool[equ.equipment.FREE],
                    planned_equipment,
                )

                if row_idx == -1:
                    Log.log_error(
                        f"Cannot find planned equipment {planned_equipment.name} "
                        f"with production id:{planned_equipment.production_id}, "
                        f"did you scrapped it?"
                    )
                    exit(1)

                Log.log_msg(
                    f"Selecting {selected_equipment.name} {selected_equipment.stars} ★"
                )
                ssw.ship_switcher.select_replacement_row(
                    row_idx=row_idx, mode=ssw.ship_switcher.EQUIPMENT_MODE
                )
                kca_u.kca.click_existing(
                    "lower_right", "shipswitcher|shiplist_shipswitch_button.png"
                )
                kca_u.kca.wait("lower", "shipswitcher|equipment_panel.png")
                api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, process_all=True)

            if (
                fleet.ships[i].slot_ex != None
                and fleet.ships[i].slot_ex.model_id != Equipment.EMPTY_EQUIPMENT
            ):
                kca_u.kca.click("reinforce_slot_equipment")

                reinforce_equipment_list = fleet.ships[
                    i
                ].available_reinforcement_equipments

                Log.log_debug_1(f"Reinforcement equipment list:")
                for k, equipment in enumerate(reinforce_equipment_list):
                    if k % 10 == 0:
                        Log.log_debug_1(f"Page {k // 10 + 1}")
                    Log.log_debug_1(
                        f"{k}: {equipment.name} {equipment.stars} (Production id: {equipment.production_id}, Model id: {equipment.model_id}), category id: {equipment.category}"
                    )

                planned_equipment = self._get_planned_equipment(
                    fleet.ships[i], "slot_ex"
                )
                if planned_equipment is None:
                    Log.log_error(
                        f"No planned reinforcement equipment assignment for "
                        f"{fleet.ships[i].name_jp}."
                    )
                    exit(1)

                row_idx, selected_equipment = self._find_equipment_row(
                    reinforce_equipment_list,
                    planned_equipment,
                )

                if row_idx == -1:
                    Log.log_error(
                        f"Cannot find planned equipment {planned_equipment.name} "
                        f"with production id:{planned_equipment.production_id}, "
                        f"did you scrapped it?"
                    )
                    exit(1)

                Log.log_msg(
                    f"Selecting {selected_equipment.name} {selected_equipment.stars} ★ on page {row_idx // 10 + 1} position {(row_idx % 10) + 1}"
                )
                ssw.ship_switcher.select_replacement_row(
                    row_idx=row_idx,
                    ship=fleet.ships[i],
                    mode=ssw.ship_switcher.REINFORCEMENT_MODE,
                )

                kca_u.kca.click_existing(
                    "lower_right", "shipswitcher|shiplist_shipswitch_button.png"
                )
                kca_u.kca.wait("lower", "shipswitcher|equipment_panel.png")
                api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, process_all=True)

        return True


def click_ship_in_equipment_page(ship_position):
    """
    method to click a ship in equipment page
    input:
        ship_position(int): position of the ship in the fleet, starts from 0
    """

    Log.log_debug_1(f"Selecting the #{ship_position + 1} ship")

    if ship_position + 1 == 7:
        next_region = Region(kca_u.kca.game_x + 262, kca_u.kca.game_y + 676, 32, 25)
        kca_u.kca.click(next_region)
        kca_u.kca.click("ship_" + str(6))
    else:
        kca_u.kca.click("ship_" + str(ship_position + 1))


fleet_switcher = FleetSwitcherCore()
