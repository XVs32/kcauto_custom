from collections.abc import Sequence
from util.pyvisauto import Region
from sys import exit
from random import choice
from random import randrange
from typing import Optional

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
from constants import (
    AUTO_PRESET,
    OTHER_FLEET_ID,
    EXPEDITION_DRUM_MODEL_ID,
    EXPEDITION_LANDING_CRAFT_MODEL_ID,
)
from fleet.fleet import Fleet
from fleet.noro6 import Noro6
from fleet_switcher.equipment_allocator import (
    EquipmentAllocationFailure,
    EquipmentAllocationResult,
    EquipmentAllocator,
    EquipmentPlan,
    EquipmentRequirement,
    EquipmentSlot,
    EquipmentSlotRef,
    EquipmentStarPreference,
    FleetTarget,
    MovableEquipment,
)
from ships.ship import Ship
from kca_enums.fleet import FleetEnum
from kca_enums.fleet_modes import FleetModeEnum
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.ship_types import ShipTypeEnum
from ships.equipment import Equipment
from util.logger import Log


class EquipmentRequirementError(Exception):
    pass


class FleetSwitcherCore(object):
    max_presets = 0
    next_combat_preset = None

    presets = {}
    custom_presets = {}
    exp_fleet_ship_id = {}
    exp_ship_pool = {}
    exp_fleet_ship_type = {}

    def __init__(self):
        self.equipment_plan = EquipmentPlan()
        self.is_noro6_validated = False
        self.equipment_allocator = EquipmentAllocator()
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

    def validate_noro6_presets(self):
        if self.is_noro6_validated:
            Log.log_debug_1("Noro6 presets are already validated")
            return

        self.is_noro6_validated = True

        if (
            not cfg.config.combat.is_auto_mode
            and not cfg.config.expedition.is_auto_mode
            and not cfg.config.pvp.is_auto_mode
        ):
            Log.log_success("kcauto is running in manual mode; Noro6 config ignored.")
            return

        if cfg.config.expedition.is_auto_mode == False:
            Log.log_warn(
                "Expedition mode is manual. Please make sure the expedition fleet does not occupy Noro6's ships and equipment."
            )
        else:
            if cfg.config.combat.is_auto_mode == False:
                Log.log_warn(
                    "Combat mode is manual; the expedition module might mess up the combat fleet on the fly."
                )

            if cfg.config.pvp.is_auto_mode == False:
                Log.log_warn(
                    "PvP mode is manual; the expedition module might mess up the PvP fleet on the fly."
                )

        noro6 = Noro6()

        for preset in noro6.presets:
            preset_name = preset["name"]

            try:
                fleets = flt.fleets.materialize_noro6_preset(noro6, preset_name)
                movable_equipments = [
                    MovableEquipment(equipment, None)
                    for equipment in equ.equipment.equipment_pool[equ.equipment.ID]
                    if equipment.production_id != Equipment.UNKNOWN_PRODUCTION_ID
                ]
                self._allocate_target_equipment(
                    list(fleets.items()),
                    movable_equipments,
                )
            except flt.Noro6MaterializationFailure as failure:
                Log.log_warn(str(failure))
            except EquipmentRequirementError as error:
                Log.log_warn(str(error))
            except EquipmentAllocationFailure as failure:
                Log.log_warn(
                    f"{preset_name}: insufficient usable equipment for model "
                    f"{failure.requirement.model_id}"
                )

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

    @property
    def _active_fleets(self):
        return flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY]

    def _find_equipment_row(
        self, equipment_list: list[Equipment], production_id: int
    ) -> int:
        for row_idx, equipment in enumerate(equipment_list):
            if equipment.production_id == production_id:
                return row_idx

        return -1

    def _get_planned_equipment_held_by_ship(
        self, ship: Ship, target_fleet: Fleet
    ) -> list[Equipment]:
        target_equipment_ids = {
            equipment.production_id
            for equipment in self.equipment_plan.equipment_for_ship_ids(
                target_fleet.ship_ids
            )
        }
        held_equipment = [
            equipment
            for equipment in ship.equipments
            if equipment.production_id in target_equipment_ids
        ]

        if (
            ship.slot_ex is not None
            and not ship.slot_ex.is_empty_equipment
            and ship.slot_ex.production_id in target_equipment_ids
        ):
            held_equipment.append(ship.slot_ex)

        return held_equipment

    def _find_safe_free_equipment_refresh_ship(
        self, target_fleets: list[Fleet]
    ) -> Optional[Ship]:
        excluded_ship_ids = {
            ship.production_id
            for target_fleet in target_fleets
            for ship in target_fleet.ships
        }

        candidates = [
            ship
            for ship in flt.fleets.ships_not_in_fleets
            if ship.locked
            and ship.production_id not in excluded_ship_ids
            and ship.ship_type != ShipTypeEnum.AR
            and ship.production_id not in rep.repair.ships_under_repair
        ]

        if not candidates:
            return None

        return candidates[randrange(len(candidates))]

    def _ensure_free_equipment_data_loaded(self, target_fleets: list[Fleet]) -> bool:
        if equ.equipment.free_equipment_initialized:
            return True

        refresh_ship = self._find_safe_free_equipment_refresh_ship(target_fleets)
        if refresh_ship is None:
            Log.log_error(
                "No safe idle ship is available to initialize free equipment data."
            )
            return False

        Log.log_msg(
            f"Free equipment data is not initialized; use {refresh_ship.name} to load it"
        )
        equ.equipment.goto()
        self.unload_ship(
            refresh_ship,
            idle_ship_list=self._idel_ships_sorted_by_equipment,
            load_random=True,
        )
        return equ.equipment.free_equipment_initialized

    def _get_movable_equipment_pool(self, context: str) -> list[MovableEquipment]:
        reserved_expedition_fleet_ids = (
            {fleet.fleet_id for fleet in flt.fleets.expedition_fleets}
            if context in ("combat", "pvp")
            else set()
        )
        movable_equipment = [
            MovableEquipment(equipment, None)
            for equipment in equ.equipment.equipment_pool[equ.equipment.FREE]
        ]

        def add_ship(ship: Ship) -> None:
            if ship.production_id in rep.repair.ships_under_repair:
                return

            for slot, equipment in enumerate(ship.equipments):
                movable_equipment.append(
                    MovableEquipment(
                        equipment,
                        EquipmentSlotRef(
                            ship.production_id, EquipmentSlot.from_index(slot)
                        ),
                    )
                )

            if ship.slot_ex is not None and not ship.slot_ex.is_empty_equipment:
                movable_equipment.append(
                    MovableEquipment(
                        ship.slot_ex,
                        EquipmentSlotRef(
                            ship.production_id, EquipmentSlot.REINFORCEMENT
                        ),
                    )
                )

        for ship in flt.fleets.ships_not_in_fleets:
            add_ship(ship)

        for fleet_id, active_fleet in self._active_fleets.items():
            if fleet_id in reserved_expedition_fleet_ids or not active_fleet.at_base:
                continue

            for ship in active_fleet.ships:
                add_ship(ship)

        return movable_equipment

    def _collect_equipment_requirements(
        self, target_fleets: list[Fleet]
    ) -> list[EquipmentRequirement]:
        requirements = []
        target_ship_ids = set()

        for target_fleet in target_fleets:
            for target_ship in target_fleet.ships:
                if target_ship.production_id in target_ship_ids:
                    raise EquipmentRequirementError(
                        f"Ship {target_ship.production_id}/{target_ship.name_jp} "
                        "is assigned to more than one target fleet."
                    )

                target_ship_ids.add(target_ship.production_id)

                active_ship = shp.ships.get_ship_from_production_id(
                    target_ship.production_id
                )
                if active_ship is None:
                    raise EquipmentRequirementError(
                        f"Ship {target_ship.production_id}/{target_ship.name_jp} "
                        "is not in the current ship pool."
                    )

                if len(target_ship.equipments) > active_ship.slot_num:
                    raise EquipmentRequirementError(
                        f"Target config for {target_ship.production_id}/{target_ship.name_jp} "
                        f"uses {len(target_ship.equipments)} normal slots, but the ship "
                        f"currently has {active_ship.slot_num}."
                    )

                for slot, target_equipment in enumerate(target_ship.equipments):
                    if target_equipment.model_id <= 0:
                        continue

                    star_preference = EquipmentStarPreference.CLOSEST
                    if target_fleet.fleet_type == FleetEnum.EXPEDITION_PRESET:
                        if (
                            target_equipment.model_id
                            == EXPEDITION_LANDING_CRAFT_MODEL_ID
                        ):
                            star_preference = EquipmentStarPreference.HIGHEST
                        elif target_equipment.model_id == EXPEDITION_DRUM_MODEL_ID:
                            star_preference = EquipmentStarPreference.ANY

                    requirements.append(
                        EquipmentRequirement.from_target_equipment(
                            target_ship.production_id,
                            EquipmentSlot.from_index(slot),
                            target_equipment,
                            star_preference,
                        )
                    )

                if target_ship.slot_ex is not None and target_ship.slot_ex.model_id > 0:
                    if active_ship.slot_ex is None:
                        raise EquipmentRequirementError(
                            f"Target config for {target_ship.production_id}/{target_ship.name_jp} "
                            "uses slot_ex, but the ship does not currently have one."
                        )
                    requirements.append(
                        EquipmentRequirement.from_target_equipment(
                            target_ship.production_id,
                            EquipmentSlot.REINFORCEMENT,
                            target_ship.slot_ex,
                        )
                    )

        return requirements

    def _allocate_target_equipment(
        self,
        targets: list[tuple[int, Fleet]],
        movable_equipments: list[MovableEquipment],
    ) -> EquipmentAllocationResult:
        target_fleets = [target_fleet for _, target_fleet in targets]
        requirements = self._collect_equipment_requirements(target_fleets)
        reinforcement_eligible_ids: dict[int, set[int]] = {}
        for requirement in requirements:
            if not requirement.slot_ref.slot.is_reinforcement:
                continue

            active_ship = shp.ships.get_ship_from_production_id(
                requirement.slot_ref.ship_id
            )
            reinforcement_eligible_ids[requirement.slot_ref.ship_id] = {
                movable.equipment.production_id
                for movable in movable_equipments
                if equ.equipment.is_reinforcement_equipment_available(
                    active_ship, movable.equipment
                )
            }

        fleet_targets = tuple(
            FleetTarget(fleet_id, tuple(target_fleet.ship_ids))
            for fleet_id, target_fleet in targets
        )
        return self.equipment_allocator.allocate(
            fleet_targets,
            requirements,
            movable_equipments,
            reinforcement_eligible_ids,
        )

    def _prepare_context_equipment_plan(
        self,
        targets: list[tuple[int, Fleet]],
        context: str,
    ) -> bool:
        target_fleets = [target_fleet for _, target_fleet in targets]
        if not target_fleets:
            self.equipment_plan = EquipmentPlan()
            return True

        if not self._ensure_free_equipment_data_loaded(target_fleets):
            return False

        movable_equipments = self._get_movable_equipment_pool(context)
        try:
            allocation = self._allocate_target_equipment(targets, movable_equipments)
        except EquipmentRequirementError as error:
            Log.log_error(str(error))
            return False
        except EquipmentAllocationFailure as failure:
            equipment = Equipment(model_id=failure.requirement.model_id)
            Log.log_error(
                "Cannot find a conflict-free equipment allocation: "
                f"insufficient usable equipment for model "
                f"{failure.requirement.model_id} ({equipment.name}) "
                "to satisfy all target slots."
            )
            return False

        self.equipment_plan = allocation.plan
        for substitution in allocation.substitutions:
            requirement = substitution.requirement
            selected_equipment = substitution.selected_equipment
            active_ship = shp.ships.get_ship_from_production_id(
                requirement.slot_ref.ship_id
            )
            requested_equipment = Equipment(model_id=requirement.model_id)
            Log.log_warn(
                f"Using {selected_equipment.name} {selected_equipment.stars}★ "
                f"({selected_equipment.production_id}) instead of requested "
                f"{requested_equipment.name} {requirement.stars}★ "
                f"(model {requirement.model_id}) for "
                f"{active_ship.name_jp} {requirement.slot_ref.slot.display_name}."
            )

        return True

    def _is_ship_equipment_assignment_matched(self, active_ship: Ship) -> bool:
        for slot in range(active_ship.slot_num):
            active_production_id = (
                active_ship.equipments[slot].production_id
                if slot < len(active_ship.equipments)
                else None
            )
            planned_equipment = self.equipment_plan.equipment_for(
                EquipmentSlotRef(
                    active_ship.production_id, EquipmentSlot.from_index(slot)
                )
            )
            planned_production_id = (
                planned_equipment.production_id
                if planned_equipment is not None
                else None
            )
            if active_production_id != planned_production_id:
                return False

        active_slot_ex_id = (
            active_ship.slot_ex.production_id
            if active_ship.slot_ex is not None
            and not active_ship.slot_ex.is_empty_equipment
            else None
        )
        planned_slot_ex = self.equipment_plan.equipment_for(
            EquipmentSlotRef(active_ship.production_id, EquipmentSlot.REINFORCEMENT)
        )
        planned_slot_ex_id = (
            planned_slot_ex.production_id if planned_slot_ex is not None else None
        )
        return active_slot_ex_id == planned_slot_ex_id

    def _is_fleet_with_planned_equipment_loaded(
        self,
        fleet_id: int,
        expected_ship_ids: Sequence[int],
    ) -> bool:
        active_fleet = self._active_fleets[fleet_id]

        if tuple(active_fleet.ship_ids) != tuple(expected_ship_ids):
            return False

        return all(
            self._is_ship_equipment_assignment_matched(active_ship)
            for active_ship in active_fleet.ships
        )

    def _log_equipment_verification_failure(self, target: FleetTarget) -> None:
        target_ship_ids = set(target.ship_ids)

        Log.log_debug_1(f"Equipment plan for fleet {target.fleet_id}:")
        for slot_ref, equipment in self.equipment_plan.assignments.items():
            if slot_ref.ship_id in target_ship_ids:
                Log.log_debug_1(f"{slot_ref}: {equipment!r}")

        Log.log_debug_1(f"Active equipment for fleet {target.fleet_id}:")
        for ship in self._active_fleets[target.fleet_id].ships:
            Log.log_debug_1(
                f"{ship.name_jp} ({ship.production_id}): "
                f"slots={ship.equipments}, slot_ex={ship.slot_ex!r}"
            )

        Log.log_error(
            f"Fleet {target.fleet_id} ships or equipment do not match the "
            "planned fleet after refresh."
        )

    def verify_equipment_plan(self) -> bool:
        for target in self.equipment_plan.targets:
            if not self._is_fleet_with_planned_equipment_loaded(
                target.fleet_id, target.ship_ids
            ):
                self._log_equipment_verification_failure(target)
                return False

        return True

    def switch_fleet(self, context):
        self.equipment_plan = EquipmentPlan()
        self.goto()
        preset_id = self._get_next_preset_id(context)

        if preset_id == AUTO_PRESET:
            if context == "combat":
                Log.log_msg(
                    f"Switching to Fleet Preset for {cfg.config.combat.sortie_map.display_name}."
                )

                fleet_list = self._get_fleet_preset(cfg.config.combat.sortie_map.value)
                if fleet_list is None:
                    return False

                # Avoiding load process of fleet 2, 3 messing up fleet 1
                # Combat is a property, sort does not saved inside it
                rev_fleet_id = flt.fleets.combat_fleets_id.copy()
                rev_fleet_id.sort(reverse=True)
                combat_targets = []

                for combat_fleet_id in rev_fleet_id:
                    target_fleet_id = 1 if combat_fleet_id == 3 else combat_fleet_id
                    target_fleet = fleet_list[target_fleet_id]
                    combat_targets.append((combat_fleet_id, target_fleet))

                if not self._prepare_context_equipment_plan(combat_targets, context):
                    return False

                for combat_fleet_id, target_fleet in combat_targets:
                    if not self._switch_to_custom_fleet_with_equipment(
                        combat_fleet_id,
                        target_fleet,
                    ):
                        return False

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
                        self._active_fleets[2].select()
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
                if fleet_list is None:
                    return False

                pvp_targets = [(1, fleet_list[1])]
                if not self._prepare_context_equipment_plan(pvp_targets, context):
                    return False

                if not self._switch_to_custom_fleet_with_equipment(1, fleet_list[1]):
                    return False

            elif context == "expedition":
                Log.log_msg(f"Switching to Exp Preset.")

                expedition_targets = []
                fleet_id = flt.fleets.get_next_exp_fleet_id()

                while (
                    fleet_id != None and exp.expedition.exp_for_fleet[fleet_id] != None
                ):
                    DEFAULT_FLEET_ID = 1
                    expedition = exp.expedition.exp_for_fleet[fleet_id]
                    fleet_list = exp.expedition.generated_expedition_fleets.get(
                        expedition
                    )
                    if fleet_list is None:
                        fleet_list = self._get_fleet_preset(
                            f"D-{expedition.expedition}"
                        )

                    if fleet_list is None:
                        Log.log_error(
                            f"No expedition fleet preset available for {expedition}."
                        )
                        return False

                    target_fleet = fleet_list[DEFAULT_FLEET_ID]
                    expedition_targets.append((fleet_id, target_fleet))
                    fleet_id = flt.fleets.get_next_exp_fleet_id(fleet_id)

                if expedition_targets and not self._prepare_context_equipment_plan(
                    expedition_targets, context
                ):
                    return False

                for fleet_id, target_fleet in expedition_targets:
                    if not self._switch_to_custom_fleet_with_equipment(
                        fleet_id,
                        target_fleet,
                    ):
                        return False

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

    def switch_to_custom_fleet(self, fleet_id, custom_fleet: Fleet):
        """
        method to switch the ship in {fleet_id} to ships defined in {ship_list}

        fleet_id(int): fleet to switch, index starts from 1
        ship_list(fleetcore_obj): ships to use
        """

        retry = 0

        while True:
            self._active_fleets[fleet_id].select()

            empty_slot_count = 0

            size = max(
                self._active_fleets[fleet_id].size,
                custom_fleet.size,
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
                if i > custom_fleet.size:
                    ship = None
                else:
                    ship = shp.ships.get_ship_from_production_id(
                        custom_fleet.ship_ids[i - 1]
                    )
                    if ship is None:
                        return False

                if i <= len(
                    self._active_fleets[fleet_id].ship_ids
                ) and shp.ships.is_same_ship(
                    ship,
                    self._active_fleets[fleet_id].ships[i - 1],
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

    def _switch_to_custom_fleet_with_equipment(
        self,
        fleet_id,
        custom_fleet: Fleet,
    ):
        """
        method to switch the ship in {fleet_id} to ships defined in {ship_list}

        fleet_id(int): fleet to switch, index starts from 1
        custom_fleet(Fleet): Fleet obj contain ships to use
        """

        if self._is_fleet_with_planned_equipment_loaded(
            fleet_id, custom_fleet.ship_ids
        ):
            Log.log_msg(f"Fleet {fleet_id} ships and equipment are already loaded")
            return True

        if not self._unload_fleet_required_equipment(custom_fleet):
            return False

        Log.log_success("Equipment unloaded.")

        nav.navigate.to("home")

        self.goto()

        if not self.switch_to_custom_fleet(fleet_id, custom_fleet):
            return False

        if not self._load_equipment(fleet_id, custom_fleet):
            return False

        Log.log_success("Equipment loaded.")
        return True

    def _scroll_preset_list(self, target_clicks):
        Log.log_debug_1(f"Scrolling to target preset ({target_clicks} clicks).")
        clicks = 0
        while clicks < target_clicks:
            kca_u.kca.click_existing("lower_left", "global|scroll_next.png")
            clicks += 1

    def _get_fleet_preset(self, key: str):
        """
        method to get the preset for combat or expedition
        input:
            key(string): the name of combat map(ex. Bm2-1-1)
        """
        fleet_list = flt.fleets.get_noro6_fleet_preset(key, warn=False)
        if fleet_list is not None:
            return fleet_list
        else:
            if key[0] == "B" or key[0] == "C":
                quest_end = key.find("-")

                Log.log_warn(
                    f"Preset {str(key)} not found, use default {key[0] + key[quest_end:]}"
                )
                key = key[0] + key[quest_end:]
            return flt.fleets.get_noro6_fleet_preset(key)

    @property
    def _idel_ships_sorted_by_equipment(self):
        temp_list = sorted(
            flt.fleets.ships_not_in_fleets,
            key=lambda item: (item.sort_id, item.production_id),
        )
        temp_list = sorted(temp_list, key=lambda s: s.level, reverse=True)

        temp_list.reverse()

        return temp_list

    def _unload_fleet_required_equipment(self, target_fleet: Fleet):
        """
        method to unload the equipments used by this fleet
        """

        nav.navigate.to("refresh_home")

        unload_ships: list[Ship] = []
        needed_load = False
        for production_id in shp.ships.ship_pool:
            ship = shp.ships.ship_pool[production_id]
            if ship.production_id in target_fleet.ship_ids:
                target_ship = target_fleet.get_ship_by_production_id(ship.production_id)

                if not self._is_ship_equipment_assignment_matched(ship):
                    needed_load = True

                    if ship.has_equipment():
                        unload_ships.append(ship)
            else:  # target_config does not care this ship, but we still have to strip it if it holds any equipment we care
                conflicts = self._get_planned_equipment_held_by_ship(ship, target_fleet)
                if conflicts:
                    unload_ships.append(ship)

        if not unload_ships:
            if not needed_load:
                Log.log_msg("No equipment to unload or load")
            else:
                Log.log_msg("No equipment needs to be unloaded")
            return True

        equ.equipment.goto()

        idle_ship_list = self._idel_ships_sorted_by_equipment
        for ship in unload_ships:
            conflicts = self._get_planned_equipment_held_by_ship(ship, target_fleet)

            if conflicts:
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

            if not self.unload_ship(
                ship,
                idle_ship_list=idle_ship_list,
            ):
                return False

        return True

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

        if ships_to_check is None:
            ships_to_check = self._idel_ships_sorted_by_equipment

        target_fleet = OTHER_FLEET_ID

        for fleet_id in self._active_fleets:
            if ship.production_id in self._active_fleets[fleet_id].ship_ids:
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
            ship_position = self._active_fleets[fleet_id].ship_ids.index(
                ship.production_id
            )

            click_ship_in_equipment_page(ship_position)

        if load_random:
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

        if ship.slot_ex is not None and not ship.slot_ex.is_empty_equipment:
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

        if self._active_fleets[fleet_id].under_repair:
            Log.log_error(
                f"Fleet {fleet_id} is under repair; equipment load process halted."
            )
            return False

        needed_load = False
        for i in range(fleet.size):
            if not self._is_ship_equipment_assignment_matched(
                self._active_fleets[fleet_id].ships[i]
            ):
                needed_load = True
                break

        if not needed_load:
            Log.log_msg(f"equipment for fleet {fleet_id} is already loaded")
            return True
        else:
            equ.equipment.goto()
            equ.equipment.goto_fleet(fleet_id)

        for i in range(fleet.size):
            if self._is_ship_equipment_assignment_matched(
                self._active_fleets[fleet_id].ships[i]
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

                if first_load:
                    kca_u.kca.click_existing(
                        "upper_right", "shipswitcher|equipment_sort_arrow.png"
                    )
                    kca_u.kca.click("equipment_sort_all")
                    first_load = False

                    kca_u.kca.wait("upper_right", "shipswitcher|equipment_sort_all.png")

                planned_equipment = self.equipment_plan.equipment_for(
                    EquipmentSlotRef(
                        fleet.ships[i].production_id, EquipmentSlot.from_index(slot)
                    )
                )
                row_idx = self._find_equipment_row(
                    equ.equipment.equipment_pool[equ.equipment.FREE],
                    planned_equipment.production_id,
                )

                if row_idx == -1:
                    Log.log_error(
                        f"Cannot find planned equipment {planned_equipment.name} "
                        f"with production id:{planned_equipment.production_id}, "
                        f"did you scrapped it?"
                    )
                    return False

                Log.log_msg(
                    f"Selecting {planned_equipment.name} {planned_equipment.stars} ★"
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
                fleet.ships[i].slot_ex is not None
                and not fleet.ships[i].slot_ex.is_empty_equipment
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

                planned_equipment = self.equipment_plan.equipment_for(
                    EquipmentSlotRef(
                        fleet.ships[i].production_id, EquipmentSlot.REINFORCEMENT
                    )
                )
                row_idx = self._find_equipment_row(
                    reinforce_equipment_list,
                    planned_equipment.production_id,
                )

                if row_idx == -1:
                    Log.log_error(
                        f"Cannot find planned equipment {planned_equipment.name} "
                        f"with production id:{planned_equipment.production_id}, "
                        f"did you scrapped it?"
                    )
                    return False

                Log.log_msg(
                    f"Selecting {planned_equipment.name} {planned_equipment.stars} ★ on page {row_idx // 10 + 1} position {(row_idx % 10) + 1}"
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
