from pyvisauto import Region
from random import choice
from sys import exit

import config.config_core as cfg
import combat.combat_core as com
import expedition.expedition_core as exp
import fleet.fleet_core as flt
import nav.nav as nav
import util.kca as kca_u
from util.logger import Log
import ship_switcher.ship_switcher_core as ssw
import ships.equipment_core as equ 
from constants import AUTO_PRESET

class FleetSwitcherCore(object):
    max_presets = 0
    presets = {}
    next_combat_preset = None
    
    custom_presets = {}
    exp_fleet_ship_id = {}
    exp_ship_pool = {}
    exp_fleet_ship_type = {}

    def __init__(self):
        self._set_next_combat_preset()

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
        elif context == "expedition":
            preset_id = AUTO_PRESET
        return preset_id

    def goto(self):
        ssw.ship_switcher.goto()

    def switch_fleet(self, context):
        self.goto()
        preset_id = self._get_next_preset_id(context)

        if preset_id == AUTO_PRESET:
            
            if context == "combat":
                Log.log_msg(f"Switching to Fleet Preset for {cfg.config.combat.sortie_map}.")

                fleet_list = self._get_fleet_preset(cfg.config.combat.sortie_map.value)
                equipment_key = self._get_equipment_preset(cfg.config.combat.sortie_map.value)
                
                for combat_fleet_id in flt.fleets.combat_fleets_id:
                    
                        
                    if not self.switch_to_costom_fleet_with_equipment(combat_fleet_id, fleet_list, equipment_key):
                        return False

                """Check if next combat possible, since new ship is switched in"""
                """Refresh home to update ship list"""
                com.combat.set_next_sortie_time(override=True)
                
            elif context == "pvp":
                Log.log_msg(f"Switching to PvP Preset.")

                fleet_list = self._get_fleet_preset("C-pvp")
                equipment_key = self._get_equipment_preset("C-pvp")
                
                        
                if not self.switch_to_costom_fleet_with_equipment(1, fleet_list, equipment_key):
                    return False

            elif context == "expedition":
                Log.log_msg(f"Switching to Exp Preset.")

                if len(exp.expedition.fleets_at_base) < 3:
                    Log.log_error("Not all expedition fleets at base.")
                    return False
                    
                for fleet_id in range(2,5):

                    if fleet_id > 4:
                        break
                    
                    
                    flag = False
                    for fleet in exp.expedition.fleets_at_base:
                        if fleet.fleet_id == fleet_id:
                            flag = True
                            break
                    if flag == False:
                        return False
                    
                    DEFAULT_FLEET_ID = 1
                    temp = {}
                    temp[fleet_id] = flt.fleets.fleets[exp.expedition.exp_for_fleet[fleet_id]][DEFAULT_FLEET_ID]
                    if not self.switch_to_costom_fleet_with_equipment(fleet_id, temp, exp.expedition.exp_for_fleet[fleet_id]):
                        return False

            elif context == 'factory_develop':
                Log.log_msg(f"Switching to {cfg.config.factory.develop_secretary} for develop.")

                ssw.ship_switcher.current_page = 1
                ssw.ship_switcher.switch_slot_by_id(1,cfg.config.factory.develop_secretary)
            elif context == 'factory_build':
                Log.log_msg(f"Switching to {cfg.config.factory.build_secretary} for construction.")

                ssw.ship_switcher.current_page = 1
                ssw.ship_switcher.switch_slot_by_id(1,cfg.config.factory.build_secretary)
        elif preset_id == None:
            Log.log_debug(f"Fleet switch disabled")
        else:
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
        return True

    def switch_to_costom_fleet(self, fleet_id, costom_fleet):
        """
            method to switch the ship in {fleet_id} to ships defined in {ship_list}

            fleet_id(int): fleet to switch, index starts from 1
            ship_list(fleetcore_obj): ships to use
        """
        
        EMPTY = -1
        retry = 0

        while True:
            
            flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].select()
            
            empty_slot_count = 0

            size = max(len(flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids), len(costom_fleet[fleet_id].ship_ids))

            any_vaild_switch = False
            retry = False
            for i in range(1,size + 1):
                if i > len(costom_fleet[fleet_id].ship_ids):
                    id = EMPTY #remove this slot
                else:
                    id = costom_fleet[fleet_id].ship_ids[i-1]

                if i <= len(flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids) and \
                    id == flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids[i-1]:
                    Log.log_debug("Ship loaded already")
                    continue

                if not ssw.ship_switcher.switch_slot_by_id(i-empty_slot_count,id):
                    #fleet data update
                    if any_vaild_switch == True:
                        Log.log_msg(f"retrying...")
                        nav.navigate.to('home')
                        self.goto()
                        retry = True 
                        break
                    else:
                        return False
                    
                else:
                    any_vaild_switch = True
                    
                if id == EMPTY:
                    empty_slot_count += 1

            if retry == True:
                continue
            else:
                break
        
        return True
        
        
    def switch_to_costom_fleet_with_equipment(self, fleet_id, costom_fleet, equipment_key):
        """
            method to switch the ship in {fleet_id} to ships defined in {ship_list}

            fleet_id(int): fleet to switch, index starts from 1
            ship_list(fleetcore_obj): ships to use
        """
        
        equ.equipment.unload_equipment(equipment_key)
        
        Log.log_success("unload_equipment done")
        
        nav.navigate.to('home')
        
        self.goto()
        
        EMPTY = -1
        retry = 0

        while True:
            
            flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].select()
            
            empty_slot_count = 0
            
            Log.log_error(f'costom_fleet: {costom_fleet[fleet_id].ship_ids}')
            Log.log_error(f'fleet_id: {fleet_id}')
            
            
            Log.log_error(f'flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY]: {flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids}')
            Log.log_error(f'fleet_id: {fleet_id}')

            size = max(len(flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids), len(costom_fleet[fleet_id].ship_ids))

            any_vaild_switch = False
            retry = False
            for i in range(1,size + 1):
                if i > len(costom_fleet[fleet_id].ship_ids):
                    id = EMPTY #remove this slot
                else:
                    id = costom_fleet[fleet_id].ship_ids[i-1]

                if i <= len(flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids) and \
                    id == flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids[i-1]:
                    Log.log_debug("Ship loaded already")
                    continue

                if not ssw.ship_switcher.switch_slot_by_id(i-empty_slot_count,id):
                    #fleet data update
                    if any_vaild_switch == True:
                        Log.log_msg(f"retrying...")
                        nav.navigate.to('home')
                        self.goto()
                        retry = True 
                        break
                    else:
                        return False
                    
                else:
                    any_vaild_switch = True
                    
                if id == EMPTY:
                    empty_slot_count += 1

            if retry == True:
                continue
            else:
                break
            
        Log.log_success("load fleet done")
            
        equ.equipment.load_equipment(fleet_id, costom_fleet[fleet_id].ship_ids, equipment_key)    
        Log.log_success("load equipment done")
        
        return True
    
    def _scroll_preset_list(self, target_clicks):
        Log.log_debug(f"Scrolling to target preset ({target_clicks} clicks).")
        clicks = 0
        while clicks < target_clicks:
            kca_u.kca.click_existing('lower_left', 'global|scroll_next.png')
            kca_u.kca.sleep(0.1)
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
            if key[0]=="B":
                
                quest_end = key.find("-")
                
                Log.log_warn(f"Preset {str(key)} not found, use default {key[0] + key[quest_end:]}")
                key = key[0] + key[quest_end:]
            else:
                Log.log_error("Unexpected preset id:" + str(key))
            return flt.fleets.fleets[key]
        
    def _get_equipment_preset(self, key):
        
        if key in flt.fleets.fleets:
            return key
        else:
            if key[0]=="B":
                
                quest_end = key.find("-")
                key = key[0] + key[quest_end:]
            else:
                Log.log_error("Unexpected preset id:" + str(key))
            return key
        
fleet_switcher = FleetSwitcherCore()
