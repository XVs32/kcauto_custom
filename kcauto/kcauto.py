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


class Kcauto(object):
    """Primary kcauto class.
    """
    end_loop_at_port = False
    is_first_print_fleet = True

    def __init__(self):
        kca_u.kca.hook_chrome(port=cfg.config.general.chrome_dev_port)

    def start_kancolle(self):
        kca_u.kca.start_kancolle()

    def find_kancolle(self):
        kca_u.kca.find_kancolle()
    
    def find_dmm(self):
        kca_u.kca.find_dmm()

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
                exp.expedition.receive_expedition()
                sts.stats.set_print_loop_end_stats()

    def run_print_fleet_logic(self):

        if not com.combat.enabled and self.is_first_print_fleet:
            self.is_first_print_fleet = False
            nav.navigate.to('refresh_home')
            flt.fleets.fleets[1].get_fleet_id_and_name()
        else:
            return False


    def fast_check_for_expedition(self):
        exp.expedition.receive_expedition()

    def run_expedition_logic(self):
        if not exp.expedition.enabled:
            return False

        if exp.expedition.expect_returned_fleets():
            self.find_kancolle()
            nav.navigate.to('home')
            self.fast_check_for_expedition()

        
        self.run_quest_logic()

        if set([ExpeditionEnum.E5_33, ExpeditionEnum.E5_34,
                ExpeditionEnum.EE_S1, ExpeditionEnum.EE_S2]) & set(
                    cfg.config.expedition.all_expeditions):
            if com.combat.time_to_sortie:
                nav.navigate.to('refresh_home')

        if exp.expedition.fleets_are_ready:
            nav.navigate.to('home')
            self.fast_check_for_expedition()
            exp.expedition.goto()
            exp.expedition.send_expeditions()
            sts.stats.set_print_loop_end_stats()

    def run_factory_logic(self):

        if not fty.factory.enabled:
            return False

        self.run_quest_logic('factory', fast_check=False)
        nav.navigate.to('home')

        anything_is_done = False

        if "F5" in qst.quest.next_check_intervals.keys():
            anything_is_done = True
            fty.factory.goto()
            if fty.factory.develop_logic(1) == True:
                self.run_quest_logic('factory', fast_check=True, back_to_home=True, force=True)
                nav.navigate.to('home')

        if "F6" in qst.quest.next_check_intervals.keys():
            anything_is_done = True
            fty.factory.goto()
            if fty.factory.build_logic(1) == True:
                self.run_quest_logic('factory', fast_check=True, back_to_home=True, force=True)
                nav.navigate.to('home')

        if "F7" in qst.quest.next_check_intervals.keys():
            anything_is_done = True
            fty.factory.goto()
            if fty.factory.develop_logic(3) == True:
                self.run_quest_logic('factory', fast_check=True, back_to_home=True, force=True)
                nav.navigate.to('home')
        
        if "F8" in qst.quest.next_check_intervals.keys():
            anything_is_done = True
            fty.factory.goto()
            """If F8 is already 80% done, one more build could finish the quest"""
            """Therefore, no if == True here"""
            fty.factory.build_logic(3)
            self.run_quest_logic('factory', fast_check=True, back_to_home=True, force=True)
            nav.navigate.to('home')

        if anything_is_done == False:
            """Daily factory process done, disable from now"""
            fty.factory.enabled = False

    def run_pvp_logic(self):
        if not pvp.pvp.enabled:
            return False

        if pvp.pvp.time_to_pvp():
            self.find_kancolle()
            self.fast_check_for_expedition()
            self.run_quest_logic('pvp')
            nav.navigate.to('home')
            self.fast_check_for_expedition()
            self._run_fleetswitch_logic('pvp')
            self.run_resupply_logic(back_to_home=True)
            sts.stats.set_print_loop_end_stats()
        else:
            return False

        pvp.pvp.goto()
        while pvp.pvp.pvp_available():
            pvp.pvp.conduct_pvp()
            self.run_resupply_logic(back_to_home=True)
            self.run_quest_logic('pvp', fast_check=True, back_to_home=True)
            if pvp.pvp.pvp_available():
                pvp.pvp.goto()
        sts.stats.set_print_loop_end_stats()
        return True

    def run_combat_logic(self):
        print("Debug: run combat logic")
        quest_selected = False
        if not com.combat.enabled:
            print("Debug: combat disabled")
            return False

        if com.combat.time_to_sortie == False:
            print("Debug: com.combat.time_to_sortie = False")
            return False

        if cfg.config.combat.sortie_map == MapEnum.auto_map_selete:
            print("Debug: Call quest combat")
            self.run_quest_logic('combat', fast_check=False, force= True)
            quest_selected = True
            if cfg.config.combat.sortie_map == MapEnum.auto_map_selete:    #If no combat map available, turn off combat module
                print("Debug: Stop combat module because no combat quest available")
                com.combat.enabled = False
                return False

        print("Debug: before should_and_able_to_sortie")
        if com.combat.should_and_able_to_sortie(ignore_supply=True):
            print("Debug: in should_and_able_to_sortie")
            if quest_selected == False:
                self.run_quest_logic('combat', fast_check=True)

            self._run_fleetswitch_logic('combat')
            self.run_resupply_logic()

            if com.combat.should_and_able_to_sortie():
                com.combat.goto()
                if com.combat.conduct_sortie():
                    sortie_queue = com.combat.get_sortie_queue()
                    if len(sortie_queue) > 1:
                        sortie_queue = sortie_queue[1:]
                        com.combat.set_sortie_queue(sortie_queue)
                        com.combat.__init__(sortie_queue[0])
                        cfg.config.combat.sortie_map = sortie_queue[0]
                    else:
                        sortie_queue = []
                        com.combat.set_sortie_queue(sortie_queue)
                        com.combat.__init__()
                        cfg.config.combat.sortie_map = ""
                    
                    sts.stats.set_print_loop_end_stats()
                    self.fast_check_for_expedition()

    def run_resupply_logic(self, back_to_home=False):
        if res.resupply.need_to_resupply:
            self.find_kancolle()
            self.fast_check_for_expedition()
            res.resupply.goto()
            res.resupply.resupply_fleets()
            self.handle_back_to_home(back_to_home)
            if not back_to_home:
                self.end_loop_at_port = True
            sts.stats.set_print_loop_end_stats()

    def run_repair_logic(self, back_to_home=False):
        if rep.repair.can_conduct_repairs:
            self.find_kancolle()
            self.fast_check_for_expedition()
            rep.repair.goto()
            rep.repair.repair_ships()
            self.handle_back_to_home(back_to_home)
            if not back_to_home:
                self.end_loop_at_port = True
            sts.stats.set_print_loop_end_stats()

    def _run_fleetswitch_logic(self, context):
        if fsw.fleet_switcher.require_fleetswitch(context):
            fsw.fleet_switcher.goto()
            fsw.fleet_switcher.switch_fleet(context)
            self.handle_back_to_home(True)

    

    def run_shipswitch_logic(self, back_to_home=False):
        
        switch_list = ssw.ship_switcher.get_ship_switch_list()
        
        if switch_list:
            nav.navigate.to('home')
            self.fast_check_for_expedition()
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
            self.fast_check_for_expedition()
            qst.quest.goto()
            qst.quest.manage_quests(context, fast_check)
            sts.stats.quest.times_checked += 1
            self.handle_back_to_home(back_to_home)
            sts.stats.set_print_loop_end_stats()

    def handle_back_to_home(self, back_to_home):
        if back_to_home:
            nav.navigate.to('home')
            self.fast_check_for_expedition()

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
