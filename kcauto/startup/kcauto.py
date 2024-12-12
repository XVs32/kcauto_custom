import os
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
import stats.stats_core as sts
import util.kca as kca_u
from kca_enums.expeditions import ExpeditionEnum
from util.logger import Log
from kca_enums.maps import MapEnum

from constants import COMBAT_CONFIG

class Kcauto(object):
    """Primary kcauto class.
    """
    end_loop_at_port = False
    is_first_print_fleet = True
    
    skip_one_repair = False

    def __init__(self):
        kca_u.kca.hook_chrome()

    def start_kancolle(self):
        kca_u.kca.start_kancolle()

    def find_kancolle(self):
        kca_u.kca.find_kancolle()
    
    def find_browser(self):
        kca_u.kca.find_browser()

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
            if not exp.expedition.receive_expedition():
                nav.navigate.to('refresh_home')
                sts.stats.set_print_loop_end_stats()

    def check_for_expedition(self):
        if not exp.expedition.receive_expedition():
            if exp.expedition.expect_returned_fleets():
                nav.navigate.to('refresh_home')
                sts.stats.set_print_loop_end_stats()

    def run_expedition_logic(self):
        if not exp.expedition.enabled:
            return False
        
        if not exp.expedition.timer.is_time_up():
            return False
           
        if exp.expedition.expect_returned_fleets() or \
          (set([ExpeditionEnum.E5_33, ExpeditionEnum.E5_34,
                ExpeditionEnum.EE_S1, ExpeditionEnum.EE_S2]) & set(
                    cfg.config.expedition.all_expeditions) and com.combat.time_to_sortie == True):
            self.find_kancolle()
            nav.navigate.to('refresh_home')

        if exp.expedition.fleets_are_ready:

            if exp.expedition.exp_for_fleet == []:

                exp.expedition.get_expedition_ranking()

                if cfg.config.expedition.fleet_preset == "auto":
                    if not flt.fleets.assign_exp_ship():
                        exp.expedition.enabled = False
                        Log.log_error(f"Failed to assign ships for self balance expedition, disable expedition module.")
                        return False
                    
            if res.resupply.exp_provisional_enabled != True:
                self.run_resupply_logic()
                 
            if exp.expedition.is_fleetswitch_needed():
                if self._run_fleetswitch_logic('expedition') != 0:
                    exp.expedition.timer.set(15*60)
                    Log.log_warn(f"Failed to switch ships for self balance expedition, disable expedition module for 15 mins.")
                    return False
                else:
                    exp.expedition.auto_assign_done = True

            exp.expedition.goto()
            exp.expedition.send_expeditions()
            self.run_quest_logic('expedition')
            sts.stats.set_print_loop_end_stats()

    def run_factory_logic(self):

        if not fty.factory.enabled or not fty.factory.disable_time_up():
            return False

        self.run_quest_logic('factory', fast_check=False)
        nav.navigate.to('home')

        anything_is_done = False

        if "F5" in qst.quest.next_check_intervals.keys():
            anything_is_done = True

            self._run_fleetswitch_logic('factory_develop')

            fty.factory.goto()
            if fty.factory.develop_logic(1) == True:
                self.run_quest_logic('factory', fast_check=True, back_to_home=True, force=True)
                nav.navigate.to('home')

        if "F6" in qst.quest.next_check_intervals.keys():
            anything_is_done = True

            self._run_fleetswitch_logic('factory_build')

            fty.factory.goto()
            if fty.factory.build_logic(1) == True:
                self.run_quest_logic('factory', fast_check=True, back_to_home=True, force=True)
                nav.navigate.to('home')
            else:
                # disable module for 60 mins
                fty.factory.set_timer()

        if "F7" in qst.quest.next_check_intervals.keys():
            anything_is_done = True

            self._run_fleetswitch_logic('factory_develop')

            fty.factory.goto()
            if fty.factory.develop_logic(3) == True:
                self.run_quest_logic('factory', fast_check=True, back_to_home=True, force=True)
                nav.navigate.to('home')
        
        if "F8" in qst.quest.next_check_intervals.keys():
            anything_is_done = True

            self._run_fleetswitch_logic('factory_build')

            fty.factory.goto()
            """If F8 is already 80% done, one more build could finish the quest"""
            """Therefore, no if == True here"""
            fty.factory.build_logic(3)
            self.run_quest_logic('factory', fast_check=True, back_to_home=True, force=True)
            nav.navigate.to('home')
            #always disable module for 15 mins
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
            nav.navigate.to('home')
            
            self.find_kancolle()
            self.run_quest_logic('pvp', back_to_home=True)
            self._run_fleetswitch_logic('pvp')
        else:
            return False

        while pvp.pvp.pvp_available():
            pvp.pvp.goto()
            pvp.pvp.conduct_pvp()
            self.run_resupply_logic(back_to_home=True)
            self.run_quest_logic('pvp', fast_check=True, back_to_home=True)
            
        sts.stats.set_print_loop_end_stats()
        return True

    def run_combat_logic(self):
        quest_selected = False
        if not com.combat.enabled or com.combat.time_to_sortie == False:
            return False
        else :
            #update port api, for _run_fleetswitch_logic
            nav.navigate.to('refresh_home')

        was_sortie_queue_empty = False
        #set sortie_queue if it is empty
        if len(com.combat.get_sortie_queue()) == 0:
            was_sortie_queue_empty = True
            Log.log_debug(f"cfg.config.combat.sortie_map_read_only:{cfg.config.combat.sortie_map_read_only}")
            if cfg.config.combat.sortie_map_read_only == MapEnum.auto_map_selete:
                self.run_quest_logic('auto_sortie', fast_check=False, back_to_home=False, force= True) #quest module will call set_sortie_queue
            else:
                Log.log_debug(f"Manual sortie mode:{cfg.config.combat.sortie_map_read_only.value}")

                sortie_queue = [cfg.config.combat.sortie_map_read_only.value]
                com.combat.set_sortie_queue(sortie_queue)
        else:
            Log.log_msg(f"Sortie queue:{com.combat.get_sortie_queue()}")


        if len(com.combat.get_sortie_queue()) == 0: #If no combat map available, turn off combat module
            Log.log_debug(f"Stop combat module cause no combat quest available")
            com.combat.enabled = False
            return False
        else:
            #update current sortie_map
            #@todo fix sortie queue map name
            cfg.config.combat.sortie_map = com.combat.get_sortie_queue()[0]

            """Check if multi stage map requested"""
            MULTI_STAGE_MAPS = {"7-2":["G", "M"], "7-3":["E", "M"], "7-5":["K", "Q", "T"]}
            GIMMICK_MAPS = {"7-5":["M"]}
            map_name = cfg.config.combat.sortie_map.value
            if map_name in MULTI_STAGE_MAPS:
                nav.navigate.to('combat')
                Log.log_error(f"com.combat.sortie_map_stage: {com.combat.sortie_map_stage}")

                try:
                    Log.log_debug(f"Gimmick needed to be finish")
                    stage = GIMMICK_MAPS[map_name][com.combat.check_gimmick()]
                except TypeError:
                    stage = MULTI_STAGE_MAPS[map_name][com.combat.sortie_map_stage - 1]
                except IndexError:
                    stage = MULTI_STAGE_MAPS[map_name][com.combat.sortie_map_stage - 1]
                except KeyError:
                    stage = MULTI_STAGE_MAPS[map_name][com.combat.sortie_map_stage - 1]


                Log.log_error(f"stage: {stage}")

                cfg.config.combat.sortie_map = cfg.config.combat.sortie_map.value + "-" + stage

        #update map_data for combat module
        com.combat.load_map_data(cfg.config.combat.sortie_map)

        if cfg.config.combat.override == False:
            #load user config
            config_json = cfg.config.load_json(cfg.config.cfg_path)
            cfg.config.combat.config_override(config_json)

            #load default config
            default_json = cfg.config.load_json(COMBAT_CONFIG + "default.json")
            cfg.config.combat.config_override(default_json)

            if os.path.isfile(COMBAT_CONFIG + cfg.config.combat.sortie_map.value + ".json"):
                default_json = cfg.config.load_json(COMBAT_CONFIG + cfg.config.combat.sortie_map.value + ".json")
                cfg.config.combat.config_override(default_json)
            elif os.path.isfile(COMBAT_CONFIG + cfg.config.combat.sortie_map.world_and_map + ".json"):
                default_json = cfg.config.load_json(COMBAT_CONFIG + cfg.config.combat.sortie_map.world_and_map + ".json")
                cfg.config.combat.config_override(default_json)
            else:
                Log.log_warn(f"{cfg.config.combat.sortie_map.value} combat config not found, use default combat config instead.")

        #apply for combat queue, assume map_data is up-to-date
        self.run_quest_logic('combat', fast_check = not was_sortie_queue_empty, force= was_sortie_queue_empty)

        port_api_update = False 
        if self._run_fleetswitch_logic('combat') == 0:
            port_api_update = True
            
        self.run_repair_logic(back_to_home=port_api_update)
        self.skip_one_repair = True
        
        if com.combat.should_and_able_to_sortie(ignore_supply=True):

            self.run_resupply_logic()
            com.combat.goto()

            if com.combat.conduct_sortie():

                Log.log_debug(f"conduct sortie end")
                #sortie success, pop the head of sortie_queue
                com.combat.pop_sortie_queue()
                
                sts.stats.set_print_loop_end_stats()
                exp.expedition.receive_expedition()
            else:
                Log.log_error(f"Sortie failed.")

    def run_resupply_logic(self, back_to_home=False):
        if res.resupply.need_to_resupply:
            self.find_kancolle()
            res.resupply.goto()
            res.resupply.resupply_fleets()
            self.handle_back_to_home(back_to_home)
            if not back_to_home:
                self.end_loop_at_port = True
            sts.stats.set_print_loop_end_stats()

    def run_repair_logic(self, back_to_home=False):
        
        if self.skip_one_repair == True:
            self.skip_one_repair = False
            return
        
        if rep.repair.can_conduct_repairs:
            self.find_kancolle()
            rep.repair.goto()
            rep.repair.repair_ships()
            self.handle_back_to_home(back_to_home)
            if not back_to_home:
                self.end_loop_at_port = True
            sts.stats.set_print_loop_end_stats()
        else:
            self.handle_back_to_home(back_to_home)
            

    def _run_fleetswitch_logic(self, context):

        """
        switch_needed = False

        while fsw.fleet_switcher.require_fleetswitch(context):
            switch_needed = True
            
            if not fsw.fleet_switcher.switch_fleet(context):
                self.handle_back_to_home(True)
                return -2
            self.handle_back_to_home(True)
            
        if switch_needed:
            return 0
        else:
            return -1
        """

        if not fsw.fleet_switcher.switch_fleet(context):
            Log.log_error(f"Failed to switch ships for {context}.")
            return -1
        self.handle_back_to_home(True)
        return 0
    

    def run_shipswitch_logic(self, back_to_home=False):
        
        switch_list = ssw.ship_switcher.get_ship_switch_list()
        
        if switch_list:
            nav.navigate.to('home')
            ssw.ship_switcher.goto()
            ssw.ship_switcher.switch_ships(switch_list)
            self.handle_back_to_home(back_to_home)
            if not back_to_home:
                self.end_loop_at_port = True

    def run_quest_logic(
            self, context=None, fast_check=False, back_to_home=False, force=False):
        if not qst.quest.enabled:
            return False

        if qst.quest.need_to_check(context) or force == True:
            self.find_kancolle()
            qst.quest.goto()
            qst.quest.manage_quests(context, fast_check)
            sts.stats.quest.times_checked += 1
            self.handle_back_to_home(back_to_home)
            sts.stats.set_print_loop_end_stats()

    def handle_back_to_home(self, back_to_home):
        if back_to_home:
            nav.navigate.to('home')

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
