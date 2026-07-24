import os
import atexit
import combat.combat_core as com
import factory.factory_core as fty
import config.config_core as cfg
import expedition.expedition_core as exp
import fleet_switcher.fleet_switcher_core as fsw
import fleet.fleet_core as flt
import nav.nav as nav
import pvp.pvp_core as pvp
import quest.quest_core as qst
import repair.repair_core as rep
import resupply.resupply_core as res
import scheduler.scheduler_core as sch
import ship_switcher.ship_switcher_core as ssw
import ships.ships_core as shp
import ships.equipment_core as equ
import stats.stats_core as sts
import util.kca as kca_u
from fleet.noro6 import Noro6
from kca_enums.expeditions import ExpeditionEnum
from kca_enums.sorite_rank import SortieRankEnum
from util.logger import Log
from kca_enums.maps import MapEnum
from quest.quest import Quest

from constants import COMBAT_CONFIG, AUTO_PRESET
from constants import CONTEXT_EXPEDITION, CONTEXT_PVP, CONTEXT_SORTIE, CONTEXT_FACTORY
from constants import CONTEXT_AUTO_EXPEDITION, CONTEXT_AUTO_SORTIE, CONTEXT_AUTO_PVP


class Kcauto(object):
    """Primary kcauto class."""

    end_loop_at_port = False
    is_first_print_fleet = True

    skip_one_repair = False

    def __init__(self):
        atexit.register(kca_u.kca.save_screenshots)
        kca_u.kca.hook_chrome()

    def start_kancolle(self):
        kca_u.kca.start_kancolle()

    def find_kancolle(self):
        kca_u.kca.find_kancolle()

    def hook_health_check(self):
        kca_u.kca.hook_health_check()

    def check_config(self):
        if cfg.config.config_changed:
            Log.log_msg("Config change detected. Loading updated config.")
            if cfg.config.initialize_config():
                com.combat.update_from_config()
                exp.expedition.update_from_config()
                pvp.pvp.update_from_config()
                qst.quest.update_from_config()
                sch.scheduler.update_from_config()

    def initialization_check(self):
        if sts.stats.rsc.ammo is None:
            Log.log_msg("kcauto is initializing.")
            if not kca_u.kca.receive_expedition():
                nav.navigate.to("refresh_home")
                sts.stats.set_print_loop_end_stats()

    def check_for_expedition(self):
        if not kca_u.kca.receive_expedition():
            if exp.expedition.expect_returned_fleets():
                nav.navigate.to("refresh_home")
                sts.stats.set_print_loop_end_stats()

    def run_expedition_logic(self):
        if not exp.expedition.enabled:
            return False

        if not exp.expedition.timer.is_time_up():
            return False

        if exp.expedition.expect_returned_fleets() or (
            set(
                [
                    ExpeditionEnum.E5_33,
                    ExpeditionEnum.E5_34,
                    ExpeditionEnum.EE_S1,
                    ExpeditionEnum.EE_S2,
                ]
            )
            & set(cfg.config.expedition.all_expeditions)
            and com.combat.time_to_sortie == True
        ):
            nav.navigate.to("refresh_home")

        if exp.expedition.fleets_are_ready:
            if cfg.config.expedition.fleet_preset == "auto":
                # get available expedition list from api
                exp.expedition.goto()
                exp.expedition.get_expedition_ranking()

                self.run_quest_logic(CONTEXT_AUTO_EXPEDITION)

                exp.expedition.prerequisite_handling()
                exp.expedition.on_going_exp_handling()
                exp.expedition.monthly_exp_handling()

                Log.log_msg(
                    f"Expedition rank: {[expedition[exp.expedition.EXP_ENUM].display_name for expedition in exp.expedition.exp_rank]}"
                )

                if not flt.fleets.assign_exp_ship():
                    exp.expedition.enabled = False
                    Log.log_error(
                        f"Failed to assign ships for self-balance expedition. Disabling expedition module."
                    )
                    return False

            if exp.expedition.is_fleetswitch_needed():
                if self._run_fleetswitch_logic("expedition") != 0:
                    exp.expedition.timer.set(15 * 60)
                    Log.log_warn(
                        f"Failed to switch ships for self-balance expedition. Disabling expedition module for 15 minutes."
                    )
                    return False

            if res.resupply.exp_provisional_enabled != True:
                self.run_resupply_logic()

            exp.expedition.goto()
            exp.expedition.send_expeditions()
            # Refresh home for exp api data update
            nav.navigate.to("refresh_home")
            self.run_quest_logic(CONTEXT_EXPEDITION)
            sts.stats.set_print_loop_end_stats()

    def run_factory_logic(self):

        if not fty.factory.enabled or not fty.factory.disable_time_up():
            return False

        self.run_quest_logic(CONTEXT_FACTORY, fast_check=False, force=True)
        nav.navigate.to("home")

        anything_is_done = False

        """@todo: check equipment pool fix 
        """
        quest_configs = [
            {
                "id": "Fd1",
                "type": "develop",
                "count": 1,
                "is_full": lambda: False,
            },
            {
                "id": "Fd3",
                "type": "develop",
                "count": 3,
                "is_full": lambda: False,
            },
            {
                "id": "Fd2",
                "type": "build",
                "count": 1,
                "is_full": shp.ships.is_ship_pool_full,
            },
            {
                "id": "Fd4",
                "type": "build",
                "count": 3,
                "is_full": shp.ships.is_ship_pool_full,
            },
        ]

        for cfg in quest_configs:
            if (
                qst.quest.is_tracking_quest(Quest(name=cfg["id"]))
                and not cfg["is_full"]()
            ):
                anything_is_done = True

                if cfg["type"] == "develop":
                    self._run_fleetswitch_logic("factory_develop")

                    fty.factory.goto()
                    if fty.factory.develop_logic(cfg["count"]) == True:
                        nav.navigate.to("home")
                else:
                    self._run_fleetswitch_logic("factory_build")

                    fty.factory.goto()

                    if not fty.factory.any_build_slot_available():
                        fty.factory.set_timer()
                        return

                    success = fty.factory.build_logic(cfg["count"])

                    if cfg["id"] == "Fd4":
                        nav.navigate.to("home")
                        fty.factory.set_timer()
                    elif success:
                        nav.navigate.to("home")
                    else:
                        fty.factory.set_timer()

        if anything_is_done == False:
            """Daily factory process done, disable from now"""
            fty.factory.enabled = False

    def run_pvp_logic(self):
        if not pvp.pvp.enabled:
            return False

        if pvp.pvp.time_to_pvp():
            pvp.pvp.goto()
            if not pvp.pvp.pvp_available():
                return False
            nav.navigate.to("home")

            if cfg.config.pvp.fleet_preset == AUTO_PRESET:
                self.run_quest_logic(
                    CONTEXT_AUTO_PVP, fast_check=False, back_to_home=False, force=True
                )

            self._run_fleetswitch_logic("pvp")
            self.run_repair_logic()

            self.run_quest_logic(CONTEXT_PVP, back_to_home=True)

        else:
            return False

        while pvp.pvp.pvp_available():
            if flt.fleets.pvp_fleets[0].under_repair == True:
                pvp.pvp.next_pvp_time = rep.repair.soonest_complete_time
                Log.log_warn(
                    f"PvP fleet is under repair, next PvP at {pvp.pvp.next_pvp_time}."
                )
                break
            self.run_resupply_logic()
            pvp.pvp.goto()
            pvp.pvp.conduct_pvp()

            qst.quest.is_quest_dom_cache_dirty = True
            self.run_quest_logic(CONTEXT_PVP, fast_check=True)

        sts.stats.set_print_loop_end_stats()
        return True

    def run_combat_logic(self):
        if not com.combat.enabled or com.combat.time_to_sortie == False:
            return False
        else:
            # update port api, for _run_fleetswitch_logic
            nav.navigate.to("refresh_home")

        was_sortie_queue_empty = False
        # set sortie_queue if it is empty
        if len(com.combat.get_sortie_queue()) == 0:
            was_sortie_queue_empty = True
            Log.log_debug_1(
                f"cfg.config.combat.sortie_map_read_only:{cfg.config.combat.sortie_map_read_only}"
            )
            if cfg.config.combat.sortie_map_read_only == MapEnum.auto_map_select:
                self.run_quest_logic(
                    CONTEXT_AUTO_SORTIE,
                    fast_check=False,
                    back_to_home=False,
                    force=True,
                )  # quest module will call set_sortie_queue
            else:
                Log.log_debug_1(
                    f"Manual sortie mode:{cfg.config.combat.sortie_map_read_only.value}"
                )

                sortie_queue = [MapEnum(cfg.config.combat.sortie_map_read_only.value)]
                com.combat.set_sortie_queue(sortie_queue)
        else:
            Log.log_msg(f"Sortie queue:{com.combat.sortie_queue}")

        if (
            len(com.combat.get_sortie_queue()) == 0
        ):  # If no combat map available, turn off combat module
            Log.log_debug_1(
                f"Stopping combat module because no combat quest is available."
            )
            com.combat.enabled = False
            return False
        else:
            # update current sortie_map
            # @todo fix sortie queue map name
            cfg.config.combat._sortie_map = com.combat.get_sortie_queue()[0]

            """Check if multi stage map requested"""
            MULTI_STAGE_MAPS = {
                MapEnum.W7_2: [MapEnum.W7_2_G, MapEnum.W7_2_M],
                MapEnum.W7_3: [MapEnum.W7_3_E, MapEnum.W7_3_P],
                MapEnum.W7_5: [MapEnum.W7_5_K, MapEnum.W7_5_Q, MapEnum.W7_5_T],
                MapEnum.W5_6: [MapEnum.W5_6_G, MapEnum.W5_6_N, MapEnum.W5_6_Z],
            }

            GIMMICK_MAPS = {
                MapEnum.W7_5: [MapEnum.W7_5_M],
                MapEnum.W5_6: [MapEnum.W5_6_R],
            }
            map_enum = cfg.config.combat.sortie_map.without_quest_and_node_enum
            if map_enum in MULTI_STAGE_MAPS:
                nav.navigate.to("combat")
                Log.log_success(f"Multi map stage: {com.combat.sortie_map_stage}")

                gimmick_await = com.combat.check_gimmick(map_enum)
                if gimmick_await is not None:
                    Log.log_debug_1(f"Gimmick needs to be finished.")
                    current_stage = gimmick_await
                    com.combat.insert_sortie_queue(current_stage)
                else:
                    try:
                        target_stage = MULTI_STAGE_MAPS[map_enum].index(
                            cfg.config.combat.sortie_map.without_quest_enum
                        )
                    except ValueError:
                        target_stage = com.combat.sortie_map_stage - 1

                    if com.combat.sortie_map_stage - 1 < target_stage:
                        current_stage = MULTI_STAGE_MAPS[map_enum][
                            com.combat.sortie_map_stage - 1
                        ]
                        com.combat.insert_sortie_queue(current_stage)
                    else:
                        current_stage = cfg.config.combat.sortie_map

                Log.log_error(f"stage: {current_stage}")
                cfg.config.combat._sortie_map = current_stage

        # update map_data for combat module
        com.combat.load_map_data(cfg.config.combat.sortie_map)

        if cfg.config.combat.override == False:
            # load user config
            config_json = cfg.config.load_json(cfg.config.cfg_path)
            cfg.config.combat.config_override(config_json)

            # load default config
            default_json = cfg.config.load_json(COMBAT_CONFIG + "default.json")
            cfg.config.combat.config_override(default_json)

            # noro6 related config override, only active when in sortie auto mode
            if cfg.config.combat.sortie_map_read_only == MapEnum.auto_map_select:
                # get combat.fleet_mode from Noro6 config
                noro6 = Noro6()
                if noro6.get_map(cfg.config.combat.sortie_map.value) == None:
                    if (
                        noro6.get_map(cfg.config.combat.sortie_map.without_quest)
                        == None
                    ):
                        Log.log_warn(
                            f"Map: {cfg.config.combat.sortie_map.without_quest} not found in Noro6 config"
                        )

                if noro6.get_fleet_mode() is not None:
                    cfg.config.combat.config_override(
                        {"combat.fleet_mode": noro6.get_fleet_mode().config_name}
                    )

            if os.path.isfile(
                COMBAT_CONFIG + cfg.config.combat.sortie_map.value + ".json"
            ):
                default_json = cfg.config.load_json(
                    COMBAT_CONFIG + cfg.config.combat.sortie_map.value + ".json"
                )
                cfg.config.combat.config_override(default_json)
            elif os.path.isfile(
                COMBAT_CONFIG + cfg.config.combat.sortie_map.without_quest + ".json"
            ):
                default_json = cfg.config.load_json(
                    COMBAT_CONFIG + cfg.config.combat.sortie_map.without_quest + ".json"
                )
                cfg.config.combat.config_override(default_json)
            elif os.path.isfile(
                COMBAT_CONFIG
                + cfg.config.combat.sortie_map.without_quest_and_node
                + ".json"
            ):
                default_json = cfg.config.load_json(
                    COMBAT_CONFIG
                    + cfg.config.combat.sortie_map.without_quest_and_node
                    + ".json"
                )
                cfg.config.combat.config_override(default_json)
            else:
                Log.log_warn(
                    f"{cfg.config.combat.sortie_map.value} combat config not found, use default combat config instead."
                )

        port_api_update = False
        if self._run_fleetswitch_logic("combat") == 0:
            port_api_update = True

        kca_u.kca.pause_if_configured("Combat fleetswitch dryrun enabled.")

        self.run_repair_logic(back_to_home=port_api_update)
        self.skip_one_repair = True

        if com.combat.should_and_able_to_sortie(ignore_supply=True):
            # apply for combat queue, assume map_data is up-to-date
            self.run_quest_logic(
                CONTEXT_SORTIE,
                fast_check=not was_sortie_queue_empty,
                force=was_sortie_queue_empty,
            )

            self.run_resupply_logic()
            com.combat.goto()

            if com.combat.conduct_sortie():
                Log.log_debug_1(f"conduct sortie end")

                selected_quest = qst.quest.auto_select_quest[CONTEXT_SORTIE]
                if selected_quest is not None:
                    current_map = (
                        cfg.config.combat.sortie_map.without_quest_and_node_enum
                    )

                    map_is_required = False
                    required_node = []
                    required_rank = SortieRankEnum["E"]
                    for required_map in selected_quest.map_context:
                        if current_map == required_map.without_quest_and_node_enum:
                            map_is_required = True
                            required_node.append(required_map.variant)  # could be None
                            required_rank = selected_quest.rank_requirement.get(
                                required_map, SortieRankEnum["E"]
                            )
                            break

                    map_is_required = (
                        selected_quest.map_context == () or map_is_required
                    )

                    if map_is_required:
                        Log.log_success(
                            f"Sortie quest {selected_quest.name} selected, current map {current_map.name} meets the map requirement."
                        )
                        last_node = com.combat.last_battle.get(com.combat.MAP_NODE)

                        if last_node is not None:
                            if required_node == []:
                                Log.log_debug_1(
                                    f"No specific node required for quest {selected_quest.name}, current node: {last_node}."
                                )
                            elif last_node.name in required_node:
                                Log.log_success(
                                    f"Required node {required_node} reached for quest {selected_quest.name}."
                                )
                                last_rank = com.combat.last_battle.get(
                                    com.combat.RANKENUM
                                )
                                if last_rank == None:
                                    Log.log_success(
                                        f"Quest {selected_quest.name} has no rank requirement, condition met with node {last_node}."
                                    )

                                elif last_rank.is_at_least(required_rank):
                                    Log.log_success(
                                        f"Quest {selected_quest.name} condition met: node {last_node} with rank {last_rank.name}."
                                    )
                                else:
                                    Log.log_warn(
                                        f"Quest {selected_quest.name} condition NOT met: node {last_node} with rank {last_rank.name} does not meet requirement of rank {required_rank.name}."
                                    )
                                    com.combat.duplicate_front_to_back_sortie_queue()
                            else:
                                Log.log_warn(
                                    f"Required node {required_node} not reached for quest {selected_quest.name}, last node: {last_node}."
                                )
                                com.combat.duplicate_front_to_back_sortie_queue()

                        else:
                            Log.log_error(
                                f"Failed to get last node from combat API, \
                                unable to verify sortie quest conditions. Map: {current_map}, required node: {required_node}."
                            )
                else:
                    Log.log_warn(
                        f"No sortie quest selected, thus no quest is progressed."
                    )

                # sortie success, pop the head of sortie_queue
                com.combat.pop_sortie_queue()

                qst.quest.is_quest_dom_cache_dirty = True
            else:
                Log.log_error(f"Sortie failed.")

            sts.stats.set_print_loop_end_stats()
            kca_u.kca.receive_expedition()

    def run_resupply_logic(self, back_to_home=False):
        if res.resupply.need_to_resupply:
            res.resupply.goto()
            res.resupply.resupply_fleets()
            self.handle_back_to_home(back_to_home)
            if not back_to_home:
                self.end_loop_at_port = True
            sts.stats.set_print_loop_end_stats()

    def run_repair_logic(self, back_to_home=False, passive_only=False):

        if self.skip_one_repair == True:
            self.skip_one_repair = False
            return

        if passive_only == True:
            # passive repair only, temporarily disable combat and pvp module
            log_temp = Log.enabled
            Log.enabled = False
            combat_temp = com.combat.enabled
            com.combat.enabled = False
            pvp_temp = pvp.pvp.enabled
            pvp.pvp.enabled = False

        if rep.repair.can_conduct_repairs:
            rep.repair.repair_ships()
            self.handle_back_to_home(back_to_home)
            if not back_to_home:
                self.end_loop_at_port = True
            sts.stats.set_print_loop_end_stats()
        else:
            self.handle_back_to_home(back_to_home)

        if passive_only == True:
            # restore combat and pvp module status
            com.combat.enabled = combat_temp
            pvp.pvp.enabled = pvp_temp
            Log.enabled = log_temp

    def _run_fleetswitch_logic(self, context):

        if not fsw.fleet_switcher.switch_fleet(context):
            Log.log_error(f"Failed to switch ships for {context}.")
            return -1
        self.handle_back_to_home(True)
        return 0

    def run_shipswitch_logic(self, back_to_home=False):

        switch_list = ssw.ship_switcher.get_ship_switch_list()

        if switch_list:
            nav.navigate.to("home")
            ssw.ship_switcher.goto()
            ssw.ship_switcher.switch_ships(switch_list)
            self.handle_back_to_home(back_to_home)
            if not back_to_home:
                self.end_loop_at_port = True

    def run_quest_logic(
        self, context=None, fast_check=False, back_to_home=False, force=False
    ):
        if not qst.quest.enabled:
            return False

        if qst.quest.need_to_check(context) or force == True:
            qst.quest.goto()
            qst.quest.manage_quests(context, fast_check)
            sts.stats.quest.times_checked += 1
            self.handle_back_to_home(back_to_home)
            sts.stats.set_print_loop_end_stats()

    def handle_back_to_home(self, back_to_home):
        if back_to_home:
            nav.navigate.to("home")

    def run_scheduler(self):
        sch.scheduler.check_and_process_rules()

    def check_end_loop_at_port(self):
        if self.end_loop_at_port:
            self.end_loop_at_port = False
            self.handle_back_to_home(True)

    @property
    def scheduler_kca_active(self):
        return sch.scheduler.kca_active

    def print_stats(self):
        if sts.stats.print_loop_end_stats:
            sts.stats.loop_count += 1
            sts.stats.print_stats()


kcauto = Kcauto()
