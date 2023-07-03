from pyvisauto import Region
from random import choice

from constants import MAX_RESOURCE, PASSIVE_TIME_INTERVAL
import api.api_core as api
import combat.combat_core as com
import config.config_core as cfg
import fleet.fleet_core as flt
import resupply.resupply_core as res
import stats.stats_core as sts
import util.kca as kca_u
from util.timer import Timer
from kca_enums.expeditions import ExpeditionEnum
from kca_enums.kcsapi_paths import KCSAPIEnum
from util.core_base import CoreBase
from util.logger import Log
from util.json_data import JsonData

class ExpeditionCore(CoreBase):
    NUM_VISIBLE_EXPEDITONS = 8
    SUPPORT_EXPEDITIONS = [
        ExpeditionEnum.E5_33, ExpeditionEnum.E5_34, ExpeditionEnum.EE_S1,
        ExpeditionEnum.EE_S2]
    _available_expeditions = []
    disable_timer = 0
    module_name = 'expedition'
    module_display_name = 'Expedition'
    available_expeditions_per_world = {}
    exp_data = None
    exp_rank = []
    exp_for_fleet = []
    TYPE_PRIORITY = [""]
    timer = None

    def __init__(self):
        """
            Method to init expedition module
        """
        super().__init__()
        self.timer = Timer()
        self.exp_data = JsonData.load_json('data|expedition|expedition.json')

   # With a normal function
    def cmp(self, item):
        return item["score"]

    def get_expedition_ranking(self):

        min_time = 0x7fffffff
        max_time = 0x00000000

        if com.combat.enabled == False:
            #Passive mode
            min_time = 0
            max_time = PASSIVE_TIME_INTERVAL
        else:
            #Active mode
            min_time = 0
            max_time = 0x7fffffff

        fuel_weight = max(MAX_RESOURCE - sts.stats.rsc.fuel, 0)
        ammo_weight = max(MAX_RESOURCE - sts.stats.rsc.ammo, 0)
        steel_weight = max(MAX_RESOURCE - sts.stats.rsc.steel, 0)
        bauxite_weight = max(MAX_RESOURCE - sts.stats.rsc.bauxite, 0)

        print(fuel_weight)
        print(ammo_weight)
        print(steel_weight)
        print(bauxite_weight)

        self.exp_rank = []

        for exp in self.exp_data:

            if exp["time"] > max_time or exp["time"] < min_time:
                continue

            id = exp["id"]

            score =(exp["fuel"]  * fuel_weight +\
                    exp["ammo"]  * ammo_weight +\
                    exp["steel"] * steel_weight +\
                    exp["baux"]  * bauxite_weight)
            
            if com.combat.enabled == True:
                #Active mode
                score /= exp["time"]
            #else:
                #Passive mode
                #score /= PASSIVE_TIME_INTERVAL #Does not affect ranking
            
            self.exp_rank.append({"id":id, "score":score})

        self.exp_rank.sort(key=self.cmp, reverse=True)
        print(self.exp_rank)

    @property
    def available_expeditions(self):
        return self._available_expeditions

    @available_expeditions.setter
    def available_expeditions(self, value):
        available_expeditions = []
        for exped in value:
            exped_id = exped['api_mission_id']
            if ExpeditionEnum.contains_value(exped_id):
                available_expeditions.append(ExpeditionEnum(exped_id))
        self._available_expeditions = available_expeditions

    def populate_available_expeditions_per_world(self):
        self.available_expeditions_per_world = {}
        for expedition in self.available_expeditions:
            world = expedition.world
            if world not in self.available_expeditions_per_world:
                self.available_expeditions_per_world[world] = [expedition]
            else:
                self.available_expeditions_per_world[world].append(expedition)

    def receive_expedition(self):

        Log.log_debug("Start receive expedetion")
        
        received_expeditions = False
        while kca_u.kca.exists(
                'expedition_flag', 'expedition|expedition_flag.png'):
            Log.log_msg("Expedition received.")
            kca_u.kca.r['shipgirl'].click()
            api.api.update_from_api({KCSAPIEnum.PORT})
            sts.stats.expedition.expeditions_received += 1
            kca_u.kca.wait('lower_right_corner', 'global|next.png', 20)
            while kca_u.kca.exists('lower_right_corner', 'global|next.png'):
                kca_u.kca.sleep()
                kca_u.kca.r['shipgirl'].click()
                kca_u.kca.r['top'].hover()
                received_expeditions = True
                kca_u.kca.sleep()
        return received_expeditions

    def expect_returned_fleets(self):
        if not com.combat.enabled and ExpeditionEnum.AUTO_0 in cfg.config.expedition.all_expeditions:
            #combat module disable, enter low ​activeness mode
            if self.timer.is_time_up():
                self.timer.set(90*60)
                return True
            else:
                return False

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
                f"Fleet {self.fleets_to_send[0].fleet_id} ready for "
                "expedition.")
            return True
        elif len(self.fleets_to_send) > 1:
            display_text = kca_u.kca.readable_list_join(
                [fleet.fleet_id for fleet in self.fleets_to_send])
            Log.log_msg(f"Fleets {display_text} ready for expedition.")
            return True
        return False

    @property
    def fleets_at_base(self):
        fleets_at_base = []
        for fleet in flt.fleets.expedition_fleets:
            if fleet.at_base:
                fleets_at_base.append(fleet)
        return fleets_at_base

    @property
    def fleets_to_send(self):
        fleets_to_send = []
        for fleet in self.fleets_at_base:
            fleet_expeditions = cfg.config.expedition.expeditions_for_fleet(
                fleet.fleet_id)
            if set(self.SUPPORT_EXPEDITIONS) & set(fleet_expeditions):
                if com.combat.should_and_able_to_sortie():
                    fleets_to_send.append(fleet)
            else:
                fleets_to_send.append(fleet)
        return fleets_to_send

    def send_expeditions(self):
        #@todo: support validate when in auto mode
        self._validate_expeditions()

        for fleet in self.fleets_to_send:
            
            if ExpeditionEnum.AUTO_0 in cfg.config.expedition.expeditions_for_fleet(fleet.fleet_id):
                expedition = ExpeditionEnum(self.exp_for_fleet[fleet.fleet_id])
            else:
                expedition = choice(
                    cfg.config.expedition.expeditions_for_fleet(
                        fleet.fleet_id))
            Log.log_msg(
                f"Sending fleet {fleet.fleet_id} to expedition "
                f"{expedition.expedition}.")
            self._select_world(expedition)
            self._select_expedition(expedition)
            if self._dispatch_expedition(fleet, expedition):
                kca_u.kca.wait('lower', 'expedition|expedition_recall.png')
                kca_u.kca.sleep(3)
            else:
                kca_u.kca.click_existing('lower', 'expedition|e_world_1.png')
                kca_u.kca.r['top'].hover()
                kca_u.kca.sleep()

    def _validate_expeditions(self):
        if len(self.available_expeditions) == 0:
            raise ValueError("No list of available expeditions found.")
        for expedition in cfg.config.expedition.all_expeditions:
            if expedition not in self.available_expeditions and expedition != ExpeditionEnum.AUTO_0:
                raise ValueError(
                    f"Specified expedition {expedition.expedition} is not "
                    "unlocked.")

    def _select_world(self, expedition):
        kca_u.kca.sleep()
        kca_u.kca.click_existing(
            'lower', f'expedition|e_world_{expedition.world}.png')

    def _select_expedition(self, expedition):
        kca_u.kca.sleep(0.1)
        expedition_list = self.available_expeditions_per_world[
            expedition.world]
        index = expedition_list.index(expedition)
        offset = 0
        if index >= self.NUM_VISIBLE_EXPEDITONS:
            if kca_u.kca.exists('lower_left', 'global|scroll_next.png'):
                self._scroll_list_down()
            offset = len(expedition_list) - self.NUM_VISIBLE_EXPEDITONS
        else:
            if kca_u.kca.exists('upper_left', 'global|scroll_prev.png'):
                self._scroll_list_up()

        true_index = index - offset
        if not 0 <= true_index < self.NUM_VISIBLE_EXPEDITONS:
            raise ValueError(f"Bad index {true_index}")
        expedition_list_region = Region(
            kca_u.kca.game_x + 190,
            kca_u.kca.game_y + 244 + (true_index * 45),
            520, 35)
        kca_u.kca.click(expedition_list_region)
        kca_u.kca.r['top'].hover()
        kca_u.kca.sleep(0.5)

    def _dispatch_expedition(self, fleet, expedition):
        if kca_u.kca.click_existing('lower_right', 'global|sortie_select.png'):
            fleet.select()
            kca_u.kca.r['top'].hover()

            if (
                    fleet.needs_resupply
                    and res.resupply.exp_provisional_enabled in (True, None)):
                res.resupply.exp_provisional_resupply(fleet)

            if fleet.needs_resupply:
                Log.log_warn(f"Fleet {fleet.fleet_id} needs resupply.")
                return False

            if kca_u.kca.click_existing(
                    'lower_right', 'expedition|expedition_dispatch.png'):
                result = api.api.update_from_api({KCSAPIEnum.EXPEDITION_START})
                sts.stats.expedition.expeditions_sent += 1
                fleet.at_base = False
                fleet.return_time = result[KCSAPIEnum.EXPEDITION_START.name][0]
                kca_u.kca.r['top'].hover()
                return True
            Log.log_warn(f"Fleet {fleet.fleet_id} is already away.")
            return False
        Log.log_warn(f"Expedition {expedition.expedition} already underway.")
        return False

    def _scroll_list_up(self):
        """Method to scroll the expedition list all the way up.
        """
        while kca_u.kca.click_existing('upper_left', 'global|scroll_prev.png'):
            pass

    def _scroll_list_down(self):
        """Method to scroll the expedition list all the way down.
        """
        while kca_u.kca.click_existing('lower_left', 'global|scroll_next.png'):
            pass


expedition = ExpeditionCore()
