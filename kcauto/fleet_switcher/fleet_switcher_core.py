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
from kca_enums.fleet import FleetEnum
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
    equipment_replacements = {}

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
        self,
        equipment_list: list[Equipment],
        target: Equipment,
        preferred_replacement_id=None,
    ):
        for row_id, equipment in enumerate(equipment_list):
            if equipment.production_id == target.production_id:
                return row_id, equipment, False

        if preferred_replacement_id is not None:
            for row_id, equipment in enumerate(equipment_list):
                if (
                    equipment.production_id == preferred_replacement_id
                    and equipment.model_id == target.model_id
                ):
                    return row_id, equipment, True

        replacement_candidates = [
            (row_id, equipment)
            for row_id, equipment in enumerate(equipment_list)
            if equipment.model_id == target.model_id
        ]
        replacement_candidates.sort(
            key=lambda item: (abs(item[1].stars - target.stars), item[1].production_id)
        )

        if replacement_candidates:
            row_id, equipment = replacement_candidates[0]
            return row_id, equipment, True

        return -1, target, False

    def _get_equipment_replacement_key(self, ship: Ship, slot):
        return (ship.production_id, slot)

    def _remember_equipment_replacement(
        self, ship: Ship, slot, target: Equipment, replacement: Equipment
    ):
        key = self._get_equipment_replacement_key(ship, slot)
        self.equipment_replacements[key] = (target, replacement)

    def _get_equipment_replacement_hint(self, ship: Ship, slot):
        key = self._get_equipment_replacement_key(ship, slot)
        replacement = self.equipment_replacements.get(key)
        return replacement[1] if replacement is not None else None

    def _restore_original_target_equipment(self, fleet: Fleet):
        for ship in fleet.ships:
            for slot, equipment in enumerate(ship.equipments):
                for key, (target, replacement) in self.equipment_replacements.items():
                    if (
                        key[0] == ship.production_id
                        and key[1] == slot
                        and equipment.production_id == replacement.production_id
                    ):
                        ship.equipments[slot] = target
                        break

            if ship.slot_ex is not None and not ship.slot_ex.is_empty_equipment:
                for key, (target, replacement) in self.equipment_replacements.items():
                    if (
                        key[0] == ship.production_id
                        and key[1] == "slot_ex"
                        and ship.slot_ex.production_id == replacement.production_id
                    ):
                        ship.slot_ex = target
                        break

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

    def _get_ship_equipment_unavailable_reason(self, ship: Ship):
        if ship.production_id in rep.repair.ships_under_repair:
            return "she is under repair"

        active_fleet = self._get_ship_active_fleet(ship)
        if active_fleet is not None and not active_fleet.at_base:
            return f"fleet {active_fleet.fleet_id} is away"

        return None

    def _format_equipment_for_log(self, equipment: Equipment):
        return f"{equipment.name} {equipment.production_id}"

    def _format_equipments_for_log(self, equipments: list[Equipment]):
        return ", ".join(
            self._format_equipment_for_log(equipment) for equipment in equipments
        )

    def _format_slot_for_log(self, slot):
        return "slot_ex" if slot == "slot_ex" else f"slot {slot + 1}"

    def _is_equipment_in_free_pool(self, equipment: Equipment):
        return any(
            free_equipment.production_id == equipment.production_id
            for free_equipment in equ.equipment.equipment_pool.get(
                equ.equipment.FREE, []
            )
        )

    def _get_equipment_holder_for_log(self, equipment: Equipment):
        if self._is_equipment_in_free_pool(equipment):
            return "free equipment list"

        for fleet_id, active_fleet in flt.fleets.fleets.get(
            flt.fleets.ACTIVE_FLEET_KEY, {}
        ).items():
            for ship in active_fleet.ships:
                for slot, equipped in enumerate(ship.equipments):
                    if equipped.production_id == equipment.production_id:
                        state = "at base" if active_fleet.at_base else "away"
                        return (
                            f"{ship.name} {self._format_slot_for_log(slot)} "
                            f"in fleet {fleet_id} ({state})"
                        )

                if (
                    ship.slot_ex is not None
                    and not ship.slot_ex.is_empty_equipment
                    and ship.slot_ex.production_id == equipment.production_id
                ):
                    state = "at base" if active_fleet.at_base else "away"
                    return f"{ship.name} slot_ex in fleet {fleet_id} ({state})"

        for ship in flt.fleets.ships_not_in_fleets:
            for slot, equipped in enumerate(ship.equipments):
                if equipped.production_id == equipment.production_id:
                    return (
                        f"{ship.name} {self._format_slot_for_log(slot)} outside fleets"
                    )

            if (
                ship.slot_ex is not None
                and not ship.slot_ex.is_empty_equipment
                and ship.slot_ex.production_id == equipment.production_id
            ):
                return f"{ship.name} slot_ex outside fleets"

        return "unknown"

    def _get_target_equipment_conflicts(self, ship: Ship, target_fleet: Fleet):
        target_equipment_ids = set(target_fleet.equipment_ids)
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

    def _get_replaceable_equipment_ships(
        self, target_fleet_id, protected_fleet_ids=None, target_ship_ids=None
    ):
        if not self._is_active_fleet_data_loaded():
            Log.log_warn(
                "Active fleet data is not loaded; limiting equipment replacement "
                "candidates to target ships and free equipment."
            )
            return []

        protected_fleet_ids = set(protected_fleet_ids or ())
        protected_fleet_ids.add(target_fleet_id)
        target_ship_ids = set(target_ship_ids or ())

        candidate_ships = []
        candidate_ship_ids = set()

        for ship in flt.fleets.ships_not_in_fleets:
            if ship.production_id in target_ship_ids:
                continue
            if not self._is_ship_equipment_replaceable(ship):
                continue
            candidate_ships.append(ship)
            candidate_ship_ids.add(ship.production_id)

        active_fleets = flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY]
        for fleet_id, active_fleet in active_fleets.items():
            if fleet_id in protected_fleet_ids or not active_fleet.at_base:
                continue

            for ship in active_fleet.ships:
                if (
                    ship.production_id in candidate_ship_ids
                    or ship.production_id in target_ship_ids
                    or not self._is_ship_equipment_replaceable(ship)
                ):
                    continue
                candidate_ships.append(ship)
                candidate_ship_ids.add(ship.production_id)

        return candidate_ships

    def _get_releasable_target_fleet_equipment_ships(
        self, target_fleet_id, target_fleet: Fleet
    ):
        if not self._is_active_fleet_data_loaded():
            return []

        active_fleet = flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY].get(
            target_fleet_id
        )
        if active_fleet is None or not active_fleet.at_base:
            return []

        candidate_ships = []
        candidate_ship_ids = set()
        for active_ship in active_fleet.ships:
            if active_ship.production_id not in target_fleet.ship_ids:
                if self._is_ship_equipment_replaceable(active_ship):
                    candidate_ships.append(active_ship)
                    candidate_ship_ids.add(active_ship.production_id)
                continue

            target_ship = target_fleet.get_ship_by_production_id(
                active_ship.production_id
            )
            if target_ship is None:
                continue

            if self._is_ship_equipment_model_matched(active_ship, target_ship):
                continue

            if self._is_ship_equipment_replaceable(active_ship):
                candidate_ships.append(active_ship)
                candidate_ship_ids.add(active_ship.production_id)

        for ship in flt.fleets.ships_not_in_fleets:
            if (
                ship.production_id not in target_fleet.ship_ids
                or ship.production_id in candidate_ship_ids
            ):
                continue

            target_ship = target_fleet.get_ship_by_production_id(ship.production_id)
            if target_ship is None:
                continue

            if self._is_ship_equipment_model_matched(ship, target_ship):
                continue

            if self._is_ship_equipment_replaceable(ship):
                candidate_ships.append(ship)
                candidate_ship_ids.add(ship.production_id)

        return candidate_ships

    def _get_equipment_replacement_candidates(
        self,
        active_ship: Ship,
        slot,
        target_equipment: Equipment,
        replaceable_ships,
    ):
        candidates_by_id = {}

        def add_candidate(priority, equipment):
            if equipment is None or equipment.model_id <= 0:
                return

            existing = candidates_by_id.get(equipment.production_id)
            if existing is None or priority < existing[0]:
                candidates_by_id[equipment.production_id] = (priority, equipment)

        if active_ship is not None and self._is_ship_equipment_replaceable(active_ship):
            for active_slot, equipment in enumerate(active_ship.equipments):
                add_candidate(0 if active_slot == slot else 1, equipment)

            add_candidate(0 if slot == "slot_ex" else 1, active_ship.slot_ex)

        for equipment in equ.equipment.equipment_pool.get(equ.equipment.FREE, []):
            add_candidate(2, equipment)

        for ship in replaceable_ships:
            for equipment in ship.equipments:
                add_candidate(3, equipment)
            add_candidate(3, ship.slot_ex)

        candidates = list(candidates_by_id.values())
        candidates.sort(
            key=lambda item: (
                item[0],
                abs(item[1].stars - target_equipment.stars),
                item[1].production_id,
            )
        )
        return candidates

    def _normalize_target_equipment(
        self, fleet_id, fleet: Fleet, protected_fleet_ids=None
    ):
        self.equipment_replacements = {}

        replaceable_ships = self._get_replaceable_equipment_ships(
            fleet_id, protected_fleet_ids, fleet.ship_ids
        )
        replaceable_ships.extend(
            self._get_releasable_target_fleet_equipment_ships(fleet_id, fleet)
        )
        target_slots = []
        candidate_map = {}

        for target_ship in fleet.ships:
            active_ship = shp.ships.get_ship_from_production_id(
                target_ship.production_id
            )
            if active_ship is not None and self._is_ship_equipment_model_matched(
                active_ship, target_ship
            ):
                Log.log_debug_1(
                    f"Skip normalizing equipment for {target_ship.name_jp} because "
                    "her equipment models already match."
                )
                continue

            for slot, target_equipment in enumerate(target_ship.equipments):
                if target_equipment.model_id <= 0:
                    continue
                key = (target_ship.production_id, slot)
                candidates = self._get_equipment_replacement_candidates(
                    active_ship, slot, target_equipment, replaceable_ships
                )
                target_slots.append((target_ship, slot, target_equipment, candidates))
                candidate_map[key] = {
                    equipment.production_id for _, equipment in candidates
                }

            if target_ship.slot_ex is not None and target_ship.slot_ex.model_id > 0:
                target_equipment = target_ship.slot_ex
                key = (target_ship.production_id, "slot_ex")
                candidates = self._get_equipment_replacement_candidates(
                    active_ship, "slot_ex", target_equipment, replaceable_ships
                )
                target_slots.append(
                    (target_ship, "slot_ex", target_equipment, candidates)
                )
                candidate_map[key] = {
                    equipment.production_id for _, equipment in candidates
                }

        reserved_exact_ids = {
            target_equipment.production_id
            for target_ship, slot, target_equipment, _ in target_slots
            if target_equipment.production_id
            in candidate_map[(target_ship.production_id, slot)]
        }
        selected_equipment_ids = set()

        for target_ship, slot, target_equipment, candidates in target_slots:
            exact_match = next(
                (
                    equipment
                    for _, equipment in candidates
                    if equipment.production_id == target_equipment.production_id
                    and equipment.production_id not in selected_equipment_ids
                ),
                None,
            )
            if exact_match is not None:
                Log.log_debug_1(
                    f"Using exact target equipment "
                    f"{self._format_equipment_for_log(exact_match)} for "
                    f"{target_ship.name_jp} {self._format_slot_for_log(slot)} "
                    f"from {self._get_equipment_holder_for_log(exact_match)}."
                )
                selected_equipment_ids.add(exact_match.production_id)
                continue

            replacement = next(
                (
                    equipment
                    for _, equipment in candidates
                    if equipment.model_id == target_equipment.model_id
                    and equipment.production_id not in selected_equipment_ids
                    and equipment.production_id not in reserved_exact_ids
                ),
                None,
            )
            if replacement is None:
                Log.log_error(
                    f"No replacement preselected for "
                    f"{target_ship.name_jp} {self._format_slot_for_log(slot)} "
                    f"targeting {self._format_equipment_for_log(target_equipment)} "
                    f"from {self._get_equipment_holder_for_log(target_equipment)}."
                )
                return False

            slot_name = "reinforcement equipment" if slot == "slot_ex" else "equipment"
            slot_label = self._format_slot_for_log(slot)
            Log.log_warn(
                f"Preselected {slot_name} {replacement.name} "
                f"with production id:{replacement.production_id} for "
                f"{target_ship.name_jp} {slot_label} as a replacement candidate "
                f"for {target_equipment.name} with production id:"
                f"{target_equipment.production_id}."
            )
            self._remember_equipment_replacement(
                target_ship, slot, target_equipment, replacement
            )
            if slot == "slot_ex":
                target_ship.slot_ex = replacement
            else:
                target_ship.equipments[slot] = replacement
            selected_equipment_ids.add(replacement.production_id)

        return True

    def _is_ship_equipment_model_matched(self, active_ship: Ship, target_ship: Ship):
        def equipment_model_ids(ship: Ship):
            model_ids = [equipment.model_id for equipment in ship.equipments]
            slot_count = max(ship.slot_num, len(model_ids))
            model_ids.extend(
                [Equipment.EMPTY_EQUIPMENT] * (slot_count - len(model_ids))
            )
            return model_ids

        if equipment_model_ids(active_ship) != equipment_model_ids(target_ship):
            return False

        active_slot_ex_model_id = (
            active_ship.slot_ex.model_id
            if active_ship.slot_ex is not None
            and not active_ship.slot_ex.is_empty_equipment
            else None
        )
        target_slot_ex_model_id = (
            target_ship.slot_ex.model_id
            if target_ship.slot_ex is not None
            and not target_ship.slot_ex.is_empty_equipment
            else None
        )
        return active_slot_ex_model_id == target_slot_ex_model_id

    def _is_custom_fleet_with_equipment_loaded(self, fleet_id, target_fleet: Fleet):
        active_fleet = flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id]

        if active_fleet.ship_ids != target_fleet.ship_ids:
            return False

        for i in range(target_fleet.size):
            active_ship = active_fleet.ships[i]
            target_ship = target_fleet.ships[i]

            if not self._is_ship_equipment_model_matched(active_ship, target_ship):
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
                for combat_fleet_id in rev_fleet_id:
                    target_fleet_id = 1 if combat_fleet_id == 3 else combat_fleet_id
                    target_ship_ids.update(fleet_list[target_fleet_id].ship_ids)

                for combat_fleet_id in rev_fleet_id:
                    if combat_fleet_id == 3:
                        fleet_list[3] = fleet_list[1]

                    if not self.switch_to_costom_fleet_with_equipment(
                        combat_fleet_id,
                        fleet_list[combat_fleet_id],
                        protected_fleet_ids,
                        target_ship_ids,
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
                fleet_id = flt.fleets.get_next_exp_fleet_id()
                while (
                    fleet_id != None and exp.expedition.exp_for_fleet[fleet_id] != None
                ):
                    DEFAULT_FLEET_ID = 1
                    temp = self._get_fleet_preset(
                        exp.expedition.exp_for_fleet[fleet_id]
                    )[DEFAULT_FLEET_ID]

                    if not self.switch_to_costom_fleet_with_equipment(
                        fleet_id, temp, protected_fleet_ids
                    ):
                        return False
                    protected_fleet_ids.add(fleet_id)
                    fleet_id = flt.fleets.get_next_exp_fleet_id(fleet_id)

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
    ):
        """
        method to switch the ship in {fleet_id} to ships defined in {ship_list}

        fleet_id(int): fleet to switch, index starts from 1
        custom_fleet(Fleet): Fleet obj contain ships to use
        """

        self._refresh_free_equipment_if_empty(
            costom_fleet, protected_fleet_ids, target_ship_ids
        )

        if not self._normalize_target_equipment(
            fleet_id, costom_fleet, protected_fleet_ids
        ):
            self._restore_original_target_equipment(costom_fleet)
            return False

        if self._is_custom_fleet_with_equipment_loaded(fleet_id, costom_fleet):
            Log.log_msg(f"Fleet {fleet_id} ships and equipment are already loaded")
            return True

        self._unload_fleet_required_equipment(
            costom_fleet, protected_fleet_ids, target_ship_ids
        )

        Log.log_success("Equipment unloaded.")

        self._restore_original_target_equipment(costom_fleet)

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

                if not self._is_ship_equipment_model_matched(ship, target_ship):
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
                        Log.log_debug_1(
                            f"Need to unload {ship.name} because target ship "
                            f"{target_ship.name_jp}'s equipment model does not match."
                        )
                        unload_ships.append(ship)
                        any_unload = True
            else:  # target_config does not care this ship, but we still have to strip it if it holds any equipment we care
                conflicts = self._get_target_equipment_conflicts(ship, target_fleet)
                if conflicts:
                    conflict_text = self._format_equipments_for_log(conflicts)
                    if ship.production_id in protected_ship_ids:
                        Log.log_warn(
                            f"Skip unloading {ship.name} because she holds target "
                            f"equipment ({conflict_text}), but her fleet is protected."
                        )
                        continue
                    if not self._is_ship_equipment_replaceable(ship):
                        reason = self._get_ship_equipment_unavailable_reason(ship)
                        Log.log_warn(
                            f"Skip unloading {ship.name} because she holds target "
                            f"equipment ({conflict_text}), but "
                            f"{reason or 'she is not available for equipment unload'}."
                        )
                        continue
                    Log.log_debug_1(
                        f"Need to unload {ship.name} because she holds target "
                        f"equipment: {conflict_text}."
                    )
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

            Log.log_msg(
                f"No equipment to unload, use {unload_ships[0].name} to update equipment list"
            )

        elif any_unload == False and needed_load == False:
            Log.log_msg(f"No equipment to unload or load")
            return False

        equ.equipment.goto()

        idle_ship_list = self._idel_ships_sorted_by_equipment
        for ship in unload_ships:
            Log.log_msg(f"Need to unload equipment for {ship.api_id}/{ship.name}")

            self.unload_ship(
                ship,
                idle_ship_list=idle_ship_list,
                load_random=(any_unload == False and needed_load == True),
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
            if not self._is_ship_equipment_model_matched(
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
            if self._is_ship_equipment_model_matched(
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

                target_equipment = fleet.ships[i].equipments[slot]
                replacement_hint = self._get_equipment_replacement_hint(
                    fleet.ships[i], slot
                )
                row_id, selected_equipment, is_replacement = self._find_equipment_row(
                    equ.equipment.equipment_pool[equ.equipment.FREE],
                    target_equipment,
                    preferred_replacement_id=(
                        replacement_hint.production_id
                        if replacement_hint is not None
                        else None
                    ),
                )

                if row_id == -1:
                    Log.log_error(
                        f"Cannot find equipment {target_equipment.name} \
                        with production id:{target_equipment.production_id}, did you scrapped it?"
                    )
                    exit(1)

                if is_replacement:
                    Log.log_warn(
                        f"Cannot find equipment {target_equipment.name} \
                        with production id:{target_equipment.production_id} in free equipment list; using \
                        production id:{selected_equipment.production_id} with {selected_equipment.stars}★ instead."
                    )

                Log.log_msg(
                    f"Selecting {selected_equipment.name} {selected_equipment.stars} ★"
                )
                ssw.ship_switcher.select_replacement_row(
                    row_idx=row_id, mode=ssw.ship_switcher.EQUIPMENT_MODE
                )
                kca_u.kca.click_existing(
                    "lower_right", "shipswitcher|shiplist_shipswitch_button.png"
                )
                kca_u.kca.wait("lower", "shipswitcher|equipment_panel.png")
                api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, process_all=True)

            if (
                fleet.ships[i].slot_ex != None
                and fleet.ships[i].slot_ex.model_id != Equipment().model_id
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

                target_equipment = fleet.ships[i].slot_ex
                replacement_hint = self._get_equipment_replacement_hint(
                    fleet.ships[i], "slot_ex"
                )
                row_id, selected_equipment, is_replacement = self._find_equipment_row(
                    reinforce_equipment_list,
                    target_equipment,
                    preferred_replacement_id=(
                        replacement_hint.production_id
                        if replacement_hint is not None
                        else None
                    ),
                )

                if row_id == -1:
                    Log.log_error(
                        f"Cannot find equipment {target_equipment.name} \
                        with production id:{target_equipment.production_id}, did you scrapped it?"
                    )
                    exit(1)

                if is_replacement:
                    Log.log_warn(
                        f"Cannot find equipment {target_equipment.name} \
                        with production id:{target_equipment.production_id} in reinforcement equipment list; using \
                        production id:{selected_equipment.production_id} with {selected_equipment.stars}★ instead."
                    )

                Log.log_msg(
                    f"Selecting {selected_equipment.name} {selected_equipment.stars} ★ on page {row_id // 10 + 1} position {(row_id % 10) + 1}"
                )
                ssw.ship_switcher.select_replacement_row(
                    row_idx=row_id,
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
