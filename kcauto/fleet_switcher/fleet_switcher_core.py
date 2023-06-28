from pyvisauto import Region
from random import choice
from sys import exit

import api.api_core as api
import config.config_core as cfg
import combat.combat_core as com
import fleet.fleet_core as flt
import nav.nav as nav
import util.kca as kca_u
from util.logger import Log
import ship_switcher.ship_switcher_core as ssw
from util.json_data import JsonData
from kca_enums.kcsapi_paths import KCSAPIEnum
from constants import AUTO_PRESET

class FleetSwitcherCore(object):
    AUTO = 0
    max_presets = 0
    presets = {}
    next_combat_preset = None
    fleet_preset = {}

    def __init__(self):
        self._set_next_combat_preset()
        self._load_fleet_preset(self._load_fleet_list())

    def _load_fleet_list(self):
        """
            method to load the setting in fleet_list.json
        """
        fleet_list = JsonData.load_json('configs|fleet_list.json')
        return fleet_list

    def _load_fleet_preset(self, fleet_list_data):
        """
            method to load the setting in fleet_preset.json
            and output the fleet preset of each map
        """
        fleet_preset_data = JsonData.load_json('configs|fleet_preset.json')
        self.fleet_preset = {}
        for map_name in fleet_preset_data:
            self.fleet_preset[map_name] = []
            for i in range(0,len(fleet_preset_data[map_name])):
                ship_type = fleet_preset_data[map_name][i]['type']
                ship_order = fleet_preset_data[map_name][i]['id']
                ship_id = fleet_list_data[ship_type][ship_order]
                self.fleet_preset[map_name].append(ship_id)


    def update_fleetpreset_data(self, data):
        # print("update_fleetpreset_data")
        self.presets = {}
        self.max_presets = data['api_max_num']
        for preset_id in data['api_deck']:
            self.presets[int(preset_id)] = [
                ship_id for ship_id in data['api_deck'][preset_id]['api_ship']
                if ship_id > -1]

    def _set_next_combat_preset(self):
        if len(cfg.config.combat.fleet_presets) > 0:
            self.next_combat_preset = choice(cfg.config.combat.fleet_presets)

    def _get_next_preset_id(self, context):
        preset_id = None
        if context == 'combat':
            preset_id = self.next_combat_preset
        elif context == 'pvp':
            preset_id = cfg.config.pvp.fleet_preset
        elif context == 'factory_develop' or context == 'factory_build':
            preset_id = AUTO_PRESET
        return preset_id

    def require_fleetswitch(self, context):
        preset_id = self._get_next_preset_id(context)
        if preset_id is None:
            return False

        if preset_id in self.presets:
            if self.presets[preset_id] == flt.fleets.fleets[1].ship_ids:
                Log.log_debug("Preset Fleet is already loaded.")
                return False

        if preset_id == AUTO_PRESET:
            if context == 'combat':
                if flt.fleets.fleets[1].ship_ids == self._get_fleet_preset(cfg.config.combat.sortie_map.value):
                    Log.log_debug("Custom preset Fleet is already loaded.")
                    return False
                else:
                    Log.log_msg("Need to switch to 'auto' preset.")

            elif context == 'factory_develop':
                if cfg.config.factory.develop_secretary == 0:
                    Log.log_warn("Develop secretary is not specified.")
                    return False
                if flt.fleets.fleets[1].ship_ids[0] == cfg.config.factory.develop_secretary:
                    Log.log_debug("Develop secretary is already loaded.")
                    return False
                else:
                    Log.log_msg("Need to switch to develop secretary.")
            elif context == 'factory_build':
                if cfg.config.factory.build_secretary == 0:
                    Log.log_warn("Build secretary is not specified.")
                    return False
                if flt.fleets.fleets[1].ship_ids[0] == cfg.config.factory.build_secretary:
                    Log.log_debug("Build secretary is already loaded.")
                    return False
                else:
                    Log.log_msg("Need to switch to build secretary.")
        else:
            Log.log_msg(f"Need to switch to Fleet Preset {preset_id}.")

        return True

    def goto(self):
        nav.navigate.to('fleetcomp')

    def switch_fleet(self, context):
        preset_id = self._get_next_preset_id(context)

        if preset_id == AUTO_PRESET:
            
            if context == 'combat':
                Log.log_msg(f"Switching to Fleet Preset for {cfg.config.combat.sortie_map}.")
                self.switch_to_costom_sleet(cfg.config.combat.sortie_map)
            elif context == 'factory_develop':
                Log.log_msg(f"Switching to {cfg.config.factory.develop_secretary} for develop.")

                ssw.ship_switcher.current_shipcomp_page = 1
                ssw.ship_switcher.switch_slot_by_id(1,cfg.config.factory.develop_secretary)
            elif context == 'factory_build':
                Log.log_msg(f"Switching to {cfg.config.factory.build_secretary} for construction.")

                ssw.ship_switcher.current_shipcomp_page = 1
                ssw.ship_switcher.switch_slot_by_id(1,cfg.config.factory.build_secretary)

            return

        Log.log_msg(f"Switching to Fleet Preset {preset_id}.")
        if preset_id not in self.presets:
            Log.log_error(
                f"Fleet Preset {preset_id} is not specified in-game. Please "
                f"check your config.")
            exit(1)

        """open preset menu"""
        kca_u.kca.click_existing(
            'lower_left', 'fleetswitcher|fleetswitch_submenu.png')
        kca_u.kca.wait(
            'lower_left', 'fleetswitcher|fleetswitch_submenu_exit.png')

        list_idx = (preset_id if preset_id < 5 else 5) - 1
        idx_offset = preset_id - 5
        if idx_offset > 0:
            kca_u.kca.sleep()
            self._scroll_preset_list(idx_offset)

        kca_u.kca.r['top'].hover()
        kca_u.kca.sleep()
        preset_idx_region = Region(
            kca_u.kca.game_x + 410,
            kca_u.kca.game_y + 275 + (list_idx * 76),
            70, 45)
        kca_u.kca.click_existing(
            preset_idx_region, 'fleetswitcher|fleetswitch_button.png')
        if kca_u.kca.exists(
                'left', 'fleetswitcher|fleetswitch_fail_check.png'):
            Log.log_error(
                f"Could not switch in fleet preset {preset_id}. Please check "
                f"your config and fleet presets.")
            exit(1)
        Log.log_msg(f"Fleet Preset {preset_id} loaded.")

        if context == 'combat':
            self._set_next_combat_preset()

    def switch_to_costom_sleet(self, map_name):
        # print("Debug: Call switch_to_costom_sleet")
        empty_slot_count = 0
        ssw.ship_switcher.current_shipcomp_page = 1

        size = max(len(flt.fleets.fleets[1].ship_ids), len(self._get_fleet_preset(map_name.value)))
        for i in range(1,size + 1):
            if i > len(self._get_fleet_preset(map_name.value)):
                id = -1 #remove this slot
                ssw.ship_switcher.switch_slot_by_id(i-empty_slot_count,id)
                empty_slot_count += 1
            else:
                id = self._get_fleet_preset(map_name.value)[i - 1]
                ssw.ship_switcher.switch_slot_by_id(i-empty_slot_count,id)

        # if flt.fleets.fleets[1].ship_ids != self._get_fleet_preset(map_name.value):
            # print("Debug: Costom fleet switch failed")
            # print(flt.fleets.fleets[1].ship_ids)
            # print(self._get_fleet_preset(map_name.value))

        """Check if next combat possible, since new ship is switched in"""
        """Refresh home to update ship list"""
        com.combat.set_next_sortie_time(override=True)

    def _scroll_preset_list(self, target_clicks):
        Log.log_debug(f"Scrolling to target preset ({target_clicks} clicks).")
        clicks = 0
        while clicks < target_clicks:
            kca_u.kca.click_existing('lower_left', 'global|scroll_next.png')
            kca_u.kca.sleep(0.1)
            clicks += 1
    
    def _get_fleet_preset(self, key):
        if key in self.fleet_preset:
            return self.fleet_preset[key]
        else:
            """If the key contain a quest name"""
            quest_name_len = len(key.split("-")[-1]) 
            if quest_name_len > 1:
                return self.fleet_preset[key[:-quest_name_len - 1]]
        raise ValueError("Unexpected preset id:" + str(key))



fleet_switcher = FleetSwitcherCore()
