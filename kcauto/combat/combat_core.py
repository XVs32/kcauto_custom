from datetime import datetime, timedelta
from operator import sub
import time
import threading

import api.api_core as api
import combat.event_reset as erst
import combat.lbas_core as lbas
import config.config_core as cfg
import fleet.fleet_core as flt
import repair.repair_core as rep
import ships.ships_core as shp
import stats.stats_core as sts
import util.kca as kca_u
from combat.map_data import MapData
from util.core_base import CoreBase
from util.json_data import JsonData
from util.kc_time import KCTime
from util.logger import Log
from kca_enums.damage_states import DamageStateEnum
from kca_enums.event_difficulties import EventDifficultyEnum
from kca_enums.fatigue_states import FatigueStateEnum
from kca_enums.formations import FormationEnum
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.maps import MapEnum
from kca_enums.nodes import NodeEnum
from kca_enums.ship_types import ShipTypeEnum


class CombatCore(CoreBase):
    COMBAT_APIS = {
        KCSAPIEnum.SORTIE_NEXT, KCSAPIEnum.SORTIE_BATTLE,
        KCSAPIEnum.SORTIE_NIGHTBATTLE, KCSAPIEnum.SORTIE_AIRBATTLE,
        KCSAPIEnum.SORTIE_LD_AIRBATTLE, KCSAPIEnum.SORTIE_LD_SHOOTING,
        KCSAPIEnum.SORTIE_N2D, KCSAPIEnum.SORTIE_NIGHT_ONLY,
        KCSAPIEnum.SORTIE_ECF_BATTLE, KCSAPIEnum.SORTIE_ECF_NIGHTBATTLE,
        KCSAPIEnum.SORTIE_CF_BATTLE, KCSAPIEnum.SORTIE_CF_NIGHTBATTLE,
        KCSAPIEnum.SORTIE_CF_AIRBATTLE, KCSAPIEnum.SORTIE_CF_WATERBATTLE,
        KCSAPIEnum.SORTIE_CF_LD_AIRBATTLE, KCSAPIEnum.SORTIE_CF_LD_SHOOTING,
        KCSAPIEnum.SORTIE_CF_N2D, KCSAPIEnum.SORTIE_CF_NIGHT_ONLY,
        KCSAPIEnum.SORTIE_CF_EACH_NIGHT_ONLY, KCSAPIEnum.SORTIE_CF_ECF_BATTLE,
        KCSAPIEnum.SORTIE_CF_ECF_AIRBATTLE,
        KCSAPIEnum.SORTIE_CF_ECF_WATERBATTLE,
        KCSAPIEnum.SORTIE_CF_ECF_LD_AIRBATTLE,
        KCSAPIEnum.SORTIE_CF_ECF_LD_SHOOTING,
        KCSAPIEnum.PORT
    }
    RESULT_APIS = {KCSAPIEnum.SORTIE_RESULT, KCSAPIEnum.SORTIE_CF_RESULT}
    SHIPDECK_API = {KCSAPIEnum.SORTIE_SHIPDECK}
    EQUIP_API = {KCSAPIEnum.SORTIE_END}
    API_COMBAT_PHASES_TYPE1 = (
        'api_hougeki', 'api_hougeki1', 'api_hougeki2', 'api_hougeki3')
    API_COMBAT_PHASES_TYPE2 = ('api_opening_atack', 'api_raigeki')
    API_COMBAT_PHASES_TYPE3 = ('api_kouku', 'api_kouku2')
    NODE_TYPE_END = 0
    NODE_TYPE_COMBAT = 1
    NODE_TYPE_COMBAT_FINISH = 2
    NODE_TYPE_SELECT = 3
    NODE_TYPE_NOTHING = 4
    NODE_TYPE_FORMATION_SKIP = 5
    module_name = 'combat'
    module_display_name = 'Combat'
    available_maps = {}
    next_sortie_time = datetime.now()
    select_nodes = []
    node_edges = None
    map_data = None
    current_node = None
    nodes_run = []
    combat_nodes_run = []
    rescued_ships = []
    boss_api = False
    map_cleared = False
    sortie_queue = []
    first_init = True
    combat_api_listener_enable = True
   
    def __init__(self):
        """
            Method to init combat module
            Args:
                sortie_map (str): The current sortie map, ex: "3-5", if input is empty, reload setting in config only
        """
        self.update_from_config()

    def update_from_config(self):
        super().update_from_config()
        if self.enabled:
            self.set_next_sortie_time()

    def update_from_combat_map(self, value):
        """
            Method to update the utility data for combat module
            only runs in auto select sortie map mode
            
            Args:
                value (str): The current sortie map, ex: "3-5"
        """
        """No map has been selected yet, it will be selected by auto map select in quest module"""
        if value == "":
            return 

        if self.enabled:
            
            quest_name_len = len(value.split("-")[-1]) 
            if quest_name_len > 1:
                value = value[:-quest_name_len - 1]

            self.load_map_data(MapEnum(value))
            self.set_next_sortie_time()
        else:
            raise ValueError("Using auto select sortie map mode but combat module disabled")



    def update_combat_map_list(self, data):
        Log.log_debug("Updating Combat map data from API.")
        self.available_maps = {}
        event_map_id_start = None
        for map_data in data:
            api_id = map_data['api_id']
            if api_id < 400:
                map_enum = MapEnum(f"B-{str(api_id)[0]}-{str(api_id)[1]}")

                self.available_maps[map_enum.world_and_map] = {
                    'enum': map_enum,
                    'cleared': map_data['api_cleared'] == 1
                }

                MULTI_STAGE_MAP_ID = [72, 73, 75]
                if api_id in MULTI_STAGE_MAP_ID:
                    self.available_maps[map_enum.world_and_map] = {
                    'gauge_num': map_data['api_gauge_num']
                    }

            else:
                if event_map_id_start is None:
                    event_map_id_start = api_id
                event_map_delta = api_id - event_map_id_start + 1
                map_enum = MapEnum(f"B-E-{event_map_delta}")

                self.available_maps[map_enum.world_and_map] = {
                    'enum': map_enum,
                    'cleared': map_data.get('api_cleared', 0) == 1,
                    'lbas_bases': map_data.get('api_air_base_decks', []),
                    'difficulty': EventDifficultyEnum(
                        map_data['api_eventmap']['api_selected_rank']),
                    'gauge_num': map_data['api_gauge_num']
                }

    def should_and_able_to_sortie(self, ignore_supply = False):
        """
            @note Port api needs to be updated before using this function
        """
        if not self.enabled or not self.time_to_sortie:
            return False
        if cfg.config.combat.port_check:
            if shp.ships.ship_count == shp.ships.max_ship_count:
                Log.log_msg("Port is full.")
                self.set_next_sortie_time(15)
                return False
        if cfg.config.combat.sortie_map == MapEnum.auto_map_selete: #No map available in auto sortie map select mode
                return False
        if cfg.config.combat.sortie_map.world == 'E':
            if shp.ships.ship_count >= shp.ships.max_ship_count - 5:
                Log.log_warn("Port is too full for event map.")
                self.set_next_sortie_time(15)
                return False
        if cfg.config.combat.check_fatigue:
            #fleet update
            for fleet in flt.fleets.combat_fleets:
                if fleet.highest_fatigue > FatigueStateEnum.NO_FATIGUE:
                    Log.log_warn("Combat fleet is fatigued.")
                    self.set_next_sortie_time(49 - fleet.lowest_morale)
                    return False
        for fleet in flt.fleets.combat_fleets:
            if fleet.under_repair:
                Log.log_warn("Combat fleet is under repair.")
                self.set_next_sortie_time(rep.repair.soonest_complete_time)
                return False
            if fleet.needs_repair:
                Log.log_warn("Combat fleet needs repair.")
                if rep.repair.docks_are_available:
                    self.set_next_sortie_time()
                else:
                    self.set_next_sortie_time(
                        rep.repair.soonest_complete_time)
                return False
            if fleet.needs_resupply and ignore_supply == False:
                Log.log_warn("Combat fleet needs resupply.")
                return False
        return True

    def set_next_sortie_time(self, value=timedelta(seconds=0), override=False):
        if isinstance(value, timedelta):
            proposed_sortie_time = datetime.now() + value
        elif isinstance(value, datetime):
            proposed_sortie_time = value
        elif isinstance(value, int):
            proposed_sortie_time = datetime.now() + timedelta(minutes=value)
        if proposed_sortie_time > self.next_sortie_time or override:
            self.next_sortie_time = proposed_sortie_time
            Log.log_msg(
                "Next sortie at "
                f"{KCTime.datetime_to_str(self.next_sortie_time)}")

    def _validate_sortie_map(self, sortie_map):
        if sortie_map.world_and_map in self.available_maps:
            return True
        return False

    @property
    def _sortie_map_is_cleared(self):
        if self.available_maps[cfg.config.combat.sortie_map.world_and_map]['cleared']:
            return True
        return False

    @property
    def sortie_map_stage(self):
        return self.available_maps[cfg.config.combat.sortie_map.world_and_map]['gauge_num']

    def load_map_data(self, sortie_map):
        Log.log_debug("Debug:load_map_data called")
        if self.map_data is None or self.map_data.name != sortie_map.world_and_map:
            Log.log_debug("Debug:load_map excute with " + str(sortie_map.world_and_map))
            data = JsonData.load_json(f'data|combat|{sortie_map.world_and_map}.json')
            self.map_data = MapData(sortie_map, data)

    @property
    def time_to_sortie(self):
        if datetime.now() >= self.next_sortie_time:
            return True
        return False

    def conduct_sortie(self):
        return self._conduct_sortie(cfg.config.combat.sortie_map)

    def _conduct_sortie(self, sortie_map):
        if not self._validate_sortie_map(sortie_map):
            Log.log_warn(f"Map {sortie_map.world_and_map} is not available.")
            return False
        if cfg.config.combat.clear_stop and self._sortie_map_is_cleared:
            Log.log_msg(f"Map {sortie_map.world_and_map} has been cleared.")
            self.enabled = False
            return False
        self._select_world(sortie_map)
        time_to_rest = lbas.lbas.manage_lbas()
        if time_to_rest:
            Log.log_warn("LBAS is fatigued.")
            self.set_next_sortie_time(time_to_rest)
            return False
        self._select_map(sortie_map)
        if self._begin_sortie():
            self.nodes_run = []
            self.combat_nodes_run = []
            self.rescued_ships = []
            self.map_cleared = False
            sts.stats.combat.combat_sorties += 1
            self._handle_combat(sortie_map)
            self._check_map_clear()
            if self.enabled:
                self.set_next_sortie_time()
            return True
        return False

    def _select_world(self, sortie_map):
        kca_u.kca.sleep()
        kca_u.kca.click_existing(
            'lower', f'combat|c_world_{sortie_map.world}.png')
        kca_u.kca.sleep()

    def _select_map(self, sortie_map):
        if sortie_map.world == 'E':
            self._select_event_map(sortie_map)
        else:
            self._select_normal_map(sortie_map)

    def _select_normal_map(self, sortie_map):
        if self.map_data.page == 2:
            kca_u.kca.click_existing('right', 'combat|c_world_eo_arrow.png')
        kca_u.kca.r['top'].hover()
        kca_u.kca.click_existing(
            'kc', f'combat|c_world_{sortie_map.world_and_map}.png')
        kca_u.kca.r['top'].hover()

    def _select_event_map(self, sortie_map):
        cur_page = 1
        if sortie_map.world == 'E':
            while cur_page < self.map_data.page:
                kca_u.kca.r['top'].hover()
                kca_u.kca.sleep(0.5)
                kca_u.kca.click_existing(
                    'kc', f'combat|_event_next_page_{cur_page}.png')
                cur_page += 1
        kca_u.kca.r['top'].hover()
        kca_u.kca.click_existing(
            'kc', f'combat|_event_world_{sortie_map.world_and_map}.png')
        if erst.reset.need_to_reset:
            erst.reset.reset_event_difficulty()
        else:
            while not kca_u.kca.exists(
                    'lower_right', 'global|sortie_select.png'):
                kca_u.kca.sleep(1)
                kca_u.kca.r['center'].click()
                kca_u.kca.sleep(1)
        kca_u.kca.r['top'].hover()

    def _begin_sortie(self):
        if kca_u.kca.click_existing('lower_right', 'global|sortie_select.png'):
            kca_u.kca.r['top'].hover()
            kca_u.sleep(2)

            sortie_button_asset = 'combat|combat_start.png'
            if lbas.lbas.enabled and len(lbas.lbas.assignable_lbas_groups) > 0:
                sortie_button_asset = 'combat|combat_start_lbas.png'

            if flt.fleets.strike_force_fleet:
                kca_u.kca.wait_and_click('upper_right', 'fleet|fleet_3.png')
                kca_u.kca.sleep()

            if kca_u.kca.click_existing('lower_right', sortie_button_asset):
                for fleet in flt.fleets.combat_fleets:
                    Log.log_msg(fleet)
                    Log.log_msg(fleet.detailed_fleet_status)
                Log.log_msg("Starting sortie.")
                return True
            Log.log_warn("Cannot start combat.")
        return False

    def _check_map_clear(self):
        if self.map_cleared:
            if cfg.config.combat.clear_stop:
                Log.log_debug("Map has been cleared!")
                self.enabled = False

    def _handle_combat(self, sortie_map):

        # Sortie start
        kca_u.kca.r['top'].hover()
        result = api.api.update_from_api({KCSAPIEnum.SORTIE_START})
        self._find_next_node(result[KCSAPIEnum.SORTIE_START.name][0])
        lbas.lbas.assign_lbas(self.map_data)

        # Next node listener start
        self.combat_api_listener_enable = True
        next_node_listener = threading.Thread(target=self._next_node_handler)
        next_node_listener.start()

        conducting_sortie = True
        while conducting_sortie == True:

            # Go to next acrion needed node
            node_type = self._cycle_between_nodes(sortie_map)
        
            if     node_type == self.NODE_TYPE_COMBAT \
                or node_type == self.NODE_TYPE_COMBAT_FINISH \
                or node_type == self.NODE_TYPE_FORMATION_SKIP :

                Log.log_msg(f"Combat at node {self.current_node}.")

                if node_type == self.NODE_TYPE_COMBAT:

                    self._resolve_smoke_prompt()

                    self._resolve_formation_prompt()
                    #api.api.update_from_api(self.COMBAT_APIS, need_all=False)

                self.combat_nodes_run.append(self.current_node)

                if self.current_node.boss_node or self.boss_api:
                    #Todo: only trigger when screen doesn't change at all
                    kca_u.kca.sleep(8)
                    Log.log_msg("Dismissing boss dialogue.")
                    kca_u.kca.r['center'].click()

                while not kca_u.kca.exists(
                        'lower_right_corner', 'global|next.png'):
                    
                    if kca_u.kca.exists('kc', 'global|combat_nb_fight.png'):
                        Log.log_debug("Night battle prompt.")

                        self._resolve_night_battle_prompt()
                        #if self._resolve_night_battle_prompt():
                            #api.api.update_from_api(self.COMBAT_APIS, need_all=False)

                        kca_u.kca.r['lbas'].hover()

                #api.api.update_from_api(self.RESULT_APIS, need_all=False)
                Log.log_debug("Battle animations complete.")
                sts.stats.combat.nodes_fought += 1
                for fleet in flt.fleets.combat_fleets:
                    kca_u.kca.wait('lower_right_corner', 'global|next.png')
                    kca_u.kca.r['center'].click()
                    kca_u.kca.r['lbas'].hover()
                    kca_u.kca.wait('kc', 'combat|mvp_marker.png')
                    kca_u.kca.sleep()
                    fleet.visual_health_check(
                        kca_u.kca.r['check_damage_combat'])
                    Log.log_msg(fleet)
                    Log.log_msg(fleet.detailed_fleet_status)
                while not (
                        kca_u.kca.exists('left', 'nav|home_menu_sortie.png')
                        or kca_u.kca.exists(
                            'lower_right', 'combat|combat_flagship_dmg.png')
                        or kca_u.kca.exists(
                            'lower', 'combat|fcf_retreat_ship.png')
                        or kca_u.kca.exists(
                            'kc', 'combat|combat_retreat.png')):
                    kca_u.kca.r['combat_click'].click()
                    kca_u.kca.sleep()

                if kca_u.kca.exists('lower', 'combat|fcf_retreat_ship.png'):
                    Log.log_error("FCF prompt is not supported yet. T^T")
                    # self._resolve_fcf_prompt()
                elif kca_u.kca.exists('kc', 'combat|combat_retreat.png'):
                    Log.log_debug("Continue sortie prompt.")
                    if self._resolve_continue_sortie_prompt():
                        Log.log_debug("Continue button pressed")
                        #api.api.update_from_api({KCSAPIEnum.SORTIE_SHIPDECK})
                    else:
                        kca_u.kca.wait('left', 'nav|home_menu_sortie.png')
                        conducting_sortie = False
                elif kca_u.kca.exists(
                        'lower_right', 'combat|combat_flagship_dmg.png'):
                    Log.log_debug("Flagship heavily damaged.")
                    conducting_sortie = False
                elif kca_u.kca.exists('left', 'nav|home_menu_sortie.png'):
                    Log.log_debug("backed to port.")
                    conducting_sortie = False

            elif node_type == self.NODE_TYPE_SELECT:
                kca_u.kca.sleep()
                Log.log_msg(f"Node select node.")
                next_node = cfg.config.combat.node_selects.get(
                    self.current_node.name, None)
                if not next_node:
                    raise ValueError("Node select not defined.")
                else:
                    Log.log_msg(f"Selecting node {next_node.value}")
                    old_node = self.current_node
                    while old_node == self.current_node:
                        self.map_data.nodes[next_node.value].select()
                        kca_u.kca.sleep()
            elif node_type == self.NODE_TYPE_NOTHING:
                pass
            elif node_type == self.NODE_TYPE_END:
                conducting_sortie = False
                continue

        self.combat_api_listener_enable = False
        next_node_listener.join()
        self._click_until_port()
        Log.log_msg(f"sortie handle end")

        return 


    def _click_until_port(self):
        while not kca_u.kca.exists('left', 'nav|home_menu_sortie.png'):
            api_result = api.api.update_from_api(
                {KCSAPIEnum.PORT} | self.SHIPDECK_API | self.EQUIP_API, need_all=False, timeout=3)
            if KCSAPIEnum.PORT.name not in api_result:
                kca_u.kca.r['combat_click'].click()

    def _next_node_handler(self):

        while self.combat_api_listener_enable:
            api_result = api.api.update_from_api(
                self.COMBAT_APIS | self.RESULT_APIS | self.SHIPDECK_API | self.EQUIP_API, need_all=True, timeout=5)
            if KCSAPIEnum.SORTIE_NEXT.name in api_result:
                self._find_next_node(
                    api_result[KCSAPIEnum.SORTIE_NEXT.name][0])
                Log.log_msg(f"Moving to Node {self.current_node}")
            elif KCSAPIEnum.PORT.name in api_result:
                Log.log_debug("Sortie ended after battle.")
                break

    def _cycle_between_nodes(self, sortie_map):
        Log.log_debug("Between nodes.")

        while True:
            if kca_u.kca.exists('kc', 'combat|compass.png'):
                Log.log_msg("Spinning compass.")
                kca_u.kca.click_existing(
                    'kc', 'combat|compass.png', cached=True)
                kca_u.kca.r['top'].hover()
            elif (  kca_u.kca.exists(
                        'formation_line_ahead',
                        'fleet|formation_line_ahead.png')
                 or kca_u.kca.exists(
                        'formation_combined_fleet_1',
                        'fleet|formation_combined_fleet_1.png')):
                return self.NODE_TYPE_COMBAT
            elif kca_u.kca.exists('lower_right_corner', 'global|next.png'):
                return self.NODE_TYPE_COMBAT_FINISH
            elif self.current_node.selection_node:
                return self.NODE_TYPE_SELECT
            elif kca_u.kca.exists('lower_right_corner', 'global|next_alt.png'):
                # resource node end
                return self.NODE_TYPE_END
            elif kca_u.kca.exists('kc', 'global|combat_nb_fight.png'):
                return self.NODE_TYPE_FORMATION_SKIP
            elif kca_u.kca.exists('left', 'nav|home_menu_sortie.png'):
                # back at home already
                return self.NODE_TYPE_END

            kca_u.kca.sleep(1)

    def _resolve_smoke_prompt(self):
        
        if NodeEnum(self.current_node.name) in cfg.config.combat.node_smoke:
            Log.log_msg("Smoke activated in config")
            if kca_u.kca.click_existing(
                'lower', 'fleet|smoke_disable.png'):
                Log.log_debug("Smoke activated")
            else:
                Log.log_debug("Smoke button not found")

    def _resolve_formation_prompt(self):
        Log.log_debug("Resolving formation prompt.")

        formation = (
            FormationEnum.COMBINED_FLEET_4
            if flt.fleets.combined_fleet
            else FormationEnum.VANGUARD)
            
        # if vanguard is not availible(not during a event)
        if not (kca_u.kca.exists(
                        'formation_vanguard',
                        'fleet|formation_vanguard.png')
            or kca_u.kca.exists(
                        'formation_combined_fleet_4',
                        'fleet|formation_combined_fleet_4.png')):
            formation = (
                FormationEnum.COMBINED_FLEET_4
                if flt.fleets.combined_fleet
                else FormationEnum.LINE_AHEAD)

        if self.current_node.name in cfg.config.combat.node_formations:
            Log.log_debug("Formation specified in config")
            formation = cfg.config.combat.node_formations[
                self.current_node.name]
        elif (
                len(self.combat_nodes_run) + 1
                in cfg.config.combat.node_formations):
            # formation resolution occurs before the combat_nodes_run list is
            # updated, so account for the 1-offset
            Log.log_debug("Formation specified combat # in config")
            formation = cfg.config.combat.node_formations[
                len(self.combat_nodes_run) + 1]
        elif self.current_node.sub_node:
            Log.log_debug("Node is sub node")
            formation = (
                FormationEnum.COMBINED_FLEET_1
                if flt.fleets.combined_fleet
                else FormationEnum.LINE_ABREAST)
        elif self.current_node.air_node:
            Log.log_debug("Node is air node")
            formation = (
                FormationEnum.COMBINED_FLEET_3
                if flt.fleets.combined_fleet
                else FormationEnum.DIAMOND)
        elif self.current_node.boss_node:
            Log.log_debug("Node is boss node")
            formation = (
                FormationEnum.COMBINED_FLEET_4
                if flt.fleets.combined_fleet
                else FormationEnum.LINE_AHEAD)

        Log.log_msg(f"Selecting formation {formation.display_name}.")
        kca_u.kca.click_existing(
            f'formation_{formation.value}',
            f'fleet|formation_{formation.value}.png')
        kca_u.kca.r['lbas'].hover()
        return formation

    def _resolve_night_battle_prompt(self):
        Log.log_debug("Resolve night battle prompt.")
        night_battle = False

        if self.current_node.name in cfg.config.combat.node_night_battles:
            Log.log_debug("NB specified in config")
            night_battle = cfg.config.combat.node_night_battles[
                self.current_node.name]
        elif (
                len(self.combat_nodes_run)
                in cfg.config.combat.node_night_battles):
            Log.log_debug("NB specified combat # in config")
            night_battle = cfg.config.combat.node_night_battles[
                len(self.combat_nodes_run)]
        elif self.current_node.boss_node:
            Log.log_debug("Node is boss node")
            night_battle = True

        if night_battle:
            Log.log_msg("Entering night battle.")
            kca_u.kca.click_existing(
                'kc', 'global|combat_nb_fight.png', cached=True)
        else:
            Log.log_msg("Declining night battle.")
            kca_u.kca.click_existing(
                'kc', 'global|combat_nb_retreat.png', cached=True)
        kca_u.kca.r['lbas'].hover()

        return night_battle

    def _resolve_continue_sortie_prompt(self):
        Log.log_debug("Resolve continue sortie prompt.")
        continue_sortie = True
        retreat_limit = cfg.config.combat.retreat_limit
        if NodeEnum(self.current_node.name) in cfg.config.combat.push_nodes:
            Log.log_msg(f"{self.current_node} is specified as a push node.")
        else:
            for fleet in flt.fleets.combat_fleets:
                if fleet.weakest_state >= retreat_limit:
                    Log.log_warn(
                        f"Fleet {fleet.fleet_id} has ships with "
                        f"{retreat_limit.display_name} damage or above.")
                    continue_sortie = False
                elif fleet.visual_health['heavy'] > 0:
                    Log.log_warn(
                        f"Fleet {fleet.fleet_id} has a critically damaged ship "
                        "not calculated from the API.")
                    continue_sortie = False
            if (
                    NodeEnum(self.current_node.name)
                    in cfg.config.combat.retreat_points):
                Log.log_debug("Retreat specified in config.")
                continue_sortie = False
            if (
                    NodeEnum(len(self.combat_nodes_run))
                    in cfg.config.combat.retreat_points):
                Log.log_debug("Retreat specified combat # in config.")
                continue_sortie = False

        if continue_sortie:
            Log.log_msg("Continuing sortie.")
            kca_u.kca.click_existing(
                'kc', 'combat|combat_continue.png', cached=True)
        else:
            Log.log_msg("Retreating from sortie.")
            kca_u.kca.click_existing(
                'kc', 'combat|combat_retreat.png', cached=True)
        kca_u.kca.r['lbas'].hover()

        return continue_sortie

    def _resolve_fcf_prompt(self):
        Log.log_debug("Resolve FCF prompt.")
        min_combat_nodes_before_fcf = 1  # extrapolate this out to config
        use_fcf = False

        if len(self.combat_nodes_run) < min_combat_nodes_before_fcf:
            return False

        heavy_damage_counter = 0
        damaged_ship = None
        damaged_ship_idx = None
        escort_ship = None
        escort_ship_idx = None

        for ship_idx, ship in enumerate(flt.fleets.combat_ships):
            if ship_idx == len(flt.fleets.combat_fleets[0].ship_data):
                # do not count the damage stage of the escort fleet flagship
                # as it is un-sinkable and un-retreatable
                pass
            if ship.damage is DamageStateEnum.HEAVY:
                Log.log_debug(f"{ship.name} is heavily damaged.")
                heavy_damage_counter += 1
                damaged_ship = ship
                damaged_ship_idx = ship_idx

        if heavy_damage_counter == 1:
            last_combat_fleet_ships = flt.fleets.combat_fleets[-1].ship_data
            for ship_idx, ship in enumerate(last_combat_fleet_ships):
                if (
                        ship.ship_type is ShipTypeEnum.DD
                        and ship.damage <= DamageStateEnum.SCRATCH):
                    Log.log_debug(f"Found {ship.name} as escort ship.")
                    escort_ship = ship
                    escort_ship_idx = ship_idx
                    break
            if not escort_ship or not escort_ship_idx:
                raise ValueError("Valid FCF retreat escort ship not found.")

            Log.log_msg(
                f"Retreating {damaged_ship.name} with {escort_ship.name} "
                "using FCF.")
            kca_u.kca.click_existing(
                'lower', 'combat|fcf_retreat_ship.png', cached=True)

            flt.fleets.combat_ships[damaged_ship_idx].hp = -1
            last_combat_fleet_ships[escort_ship_idx].hp = -1
            sts.stats.combat.fcfs_done += 1
            use_fcf = True
        else:
            Log.log_msg("Not retreating ships using FCF.")
            kca_u.kca.click_existing(
                'lower', 'combat|fcf_continue_fleet.png', cached=True)
        kca_u.kca.r['lbas'].hover()

        return use_fcf

    def predict_battle(self, data):
        Log.log_debug("Predicting battle from data.")
        if 'api_flavor_info' in data:
            Log.log_debug("Boss node detected via API.")
            self.boss_api = True
            # if 'api_midnight_flag' in data:
            #     print(f"nightbattle: {data['api_midnight_flag']}")

        new_hps = (
            list(data['api_f_nowhps'] + data['api_f_nowhps_combined'])
            if flt.fleets.combined_fleet
            else list(data['api_f_nowhps']))
        new_hps = self._calculate_hps(new_hps, data)
        Log.log_debug(f"Calculated HPs: {new_hps}")
        fleet_1_size = len(flt.fleets.combat_fleets[0].ship_data)
        flt.fleets.combat_fleets[0].update_ship_hps(new_hps[0:fleet_1_size])
        Log.log_msg(flt.fleets.combat_fleets[0])
        if flt.fleets.combined_fleet:
            flt.fleets.combat_fleets[1].update_ship_hps(new_hps[fleet_1_size:])
            Log.log_msg(flt.fleets.combat_fleets[1])

    def process_battle_result(self, data):
        Log.log_debug("Processing battle results.")
        if 'api_first_clear' in data:
            cleared = data['api_first_clear'] == 1
            if cleared:
                Log.log_debug("Map has been cleared.")
                self.map_cleared = True
        if 'api_get_ship' in data:
            dropped_ship_id = data['api_get_ship']['api_ship_id']
            # Add temp empty local static data ship to ship pool, 
            # data will be updated when back to port
            ship = shp.ships.create_ship(
                static_data = shp.ships.get_ship_static_data(dropped_ship_id))
            self.rescued_ships.append(ship)
            Log.log_success(f"Rescued {ship.name} (#{ship.sortno}).")
            sts.stats.combat.ships_rescued += 1

    def _calculate_hps(self, new_hps, data):
        for phase in self.API_COMBAT_PHASES_TYPE1:
            if phase in data and data[phase] is not None:
                new_hps = self._calculate_hps_from_type1(new_hps, data[phase])
        for phase in self.API_COMBAT_PHASES_TYPE2:
            if phase in data and data[phase] is not None:
                new_hps = self._calculate_hps_from_type2(new_hps, data[phase])
        for phase in self.API_COMBAT_PHASES_TYPE3:
            if phase in data and data[phase]['api_stage3'] is not None:
                new_hps = self._calculate_hps_from_type3(new_hps, data[phase])
        return new_hps

    def _calculate_hps_from_type1(self, hps, api_data):
        hps = list(hps)
        e_actions = api_data['api_at_eflag']
        dmgs = api_data['api_damage']
        targets = api_data['api_df_list']
        for idx, e_action in enumerate(e_actions):
            if e_action == 0:
                continue
            for t_idx, target in enumerate(targets[idx]):
                hps[target] -= dmgs[idx][t_idx]
        return hps

    def _calculate_hps_from_type2(self, hps, api_data):
        hps = list(hps)
        dmgs = api_data['api_fdam']
        return list(map(sub, hps, dmgs))

    def _calculate_hps_from_type3(self, hps, api_data):
        hps = list(hps)
        dmgs = (list(api_data['api_stage3']['api_fdam'] +
                     api_data['api_stage3_combined']['api_fdam'])
            if flt.fleets.combined_fleet
            else list(api_data['api_stage3']['api_fdam']))
        return list(map(sub, hps, dmgs))

    def _find_next_node(self, edge):
        next_node = self._get_next_node_from_edge(edge)
        Log.log_msg(f"Going to Node {next_node}")
        self.current_node = next_node
        self.nodes_run.append(next_node)

    def _get_next_node_from_edge(self, edge):
        Log.log_msg(f"self.map_data.name {self.map_data.name}")
        # print("Debug:"+ str( self.map_data.name))
        return self.map_data.edges[edge][1]

    def set_sortie_queue(self, sortie_queue = []):
        """
            method for other modules to set the sortie_queue in combat module
            Args:
                sortie_queue (str list): A list of sortie_map, ex: ["1-1", "2-3"]
        """
        self.sortie_queue = sortie_queue.copy()
        Log.log_msg(f"Set sortie queue {self.sortie_queue}")


    def get_sortie_queue(self):
        """
            method for other modules to read the sortie_queue in combat module
        """
        return self.sortie_queue
    
    def pop_sortie_queue(self):
        """
            method to pop the head of sortie_queue
        """
        if len(self.sortie_queue) > 0:
            self.sortie_queue.pop(0)
            Log.log_msg(f"Sortie queue updated:{self.sortie_queue}")
        else:
            Log.log_error(f"cannot pop an empty queue(sortie_queue)")

        return self.sortie_queue

    def solve_gimmick(self):

        data = JsonData.load_json(f'data|temp|gimmick.json')

        try:
            data[self.sortie_queue]["gimmick_level"] += 1
            JsonData.dump_json(data, 'data|temp|gimmick.json')
            
        except KeyError:
            Log.log_debug("Invalid gimmick update requested.")
    def check_gimmick(self):
        """
            method to check what gimmick to go next for the current sortie map
            return None if no gimmick is availble
        """
        data = JsonData.load_json(f'data|temp|gimmick.json')
        map_name = cfg.config.combat.sortie_map.value

        """Reset gimmick each month"""
        try:
            if not KCTime.is_same_month(data[map_name]["timestamp"], time.time()):
                Log.log_debug("Gimmick renew")
                data[map_name]["timestamp"] = time.time()
                data[map_name]["gimmick_level"] = 0
                JsonData.dump_json(data, 'data|temp|gimmick.json')
        except KeyError:
            pass

        gimmick_level = None

        """gimmick_level rules for each map(7-5 only for now)"""
        if map_name == "7-5"\
        and (self.sortie_map_stage - 1) >= 1:
            try:
                gimmick_level = data[map_name]["gimmick_level"]
            except KeyError:
                pass

        return gimmick_level

combat = CombatCore()
