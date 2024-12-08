from pyvisauto import Region
from random import choice
from sys import exit
import re
import copy
import shutil

import config.config_core as cfg
import combat.combat_core as com
import expedition.expedition_core as exp
import fleet.fleet_core as flt
import nav.nav as nav
import util.kca as kca_u
from util.logger import Log
import ship_switcher.ship_switcher_core as ssw
import ships.equipment_core as equ 
from util.json_data import JsonData
from constants import AUTO_PRESET

class FleetSwitcherCore(object):
    AUTO = 0
    max_presets = 0
    presets = {}
    next_combat_preset = None
    
    custom_presets = {}
    exp_fleet_ship_id = {}
    exp_ship_pool = {}
    exp_fleet_ship_type = {}

    def __init__(self):
        self._set_next_combat_preset()

    def _load_ship_pool(self):
        """
            method to load the setting in ship_pool.json
        """
        # open the file for reading
        try:
            ship_pool = JsonData.load_json('configs|ship_pool.json')
        except FileNotFoundError:
            ship_pool = JsonData.load_json('data|config|ship_pool.json')
            shutil.copyfile('data/config/ship_pool.json', 'configs/ship_pool.json')
        return ship_pool

       

    def _get_fleet_ship_id(self, fleet_ship_type, ship_pool):
        """
            Method to get the ship id list from ship type and ship pool

            input: 
                fleet_ship_type: The fleet list
                    ex: [{'type': 'DD', 'id': 0}, 
                            {'type': 'DD', 'id': 1}, 
                            {'type': 'DD', 'id': 2}, 
                            {'type': 'DD', 'id': 3}, 
                            {'type': 'DD', 'id': 4}, 
                            {'type': 'DD', 'id': 5}]
                ship_pool(dict): The pool of ship to use
                    ex. {"DD":[10,20,30], "CL":[41,42,43]}
            
            output:
                ship_list[]: The ship id list converted from ship type and ship pool
                    ex: [15, 27, 2, 93, 3, 7]
        """
        ship_list = []
        for i in range(0,len(fleet_ship_type)):
            ship_type = fleet_ship_type[i]['type']
            ship_order = fleet_ship_type[i]['id']
            ship_id = ship_pool[ship_type][ship_order]
            ship_list.append(ship_id)

        return ship_list

    def update_fleetpreset_data(self, data):
        # print("update_fleetpreset_data")
        self.presets = {}
        self.max_presets = data['api_max_num']
        for preset_id in data['api_deck']:
            self.presets[int(preset_id)] = [
                ship_id for ship_id in data['api_deck'][preset_id]['api_ship']
                if ship_id > -1]

    def assign_exp_ship(self):

        FLEET_ID_OFFSET = 2

        ship_pool = self._load_ship_pool()

        self.custom_presets["exp"] = {}
        exp.expedition.exp_for_fleet = [None, None, None, None, None]
        fleet_id = 1
        fleet_id = self._get_next_exp_fleet_id(fleet_id)
        for exp_rank in exp.expedition.exp_rank:

            ship_pool_bak = copy.deepcopy(ship_pool)


            fleetShipId, ship_pool = self._assign_ship( \
                self.exp_fleet_ship_type[exp_rank["id"]], \
                ship_pool,
                exp.expedition.exp_data[exp_rank["id"] - 1]["reqDrum"],
                exp.expedition.exp_data[exp_rank["id"] - 1]["reqDrumCarriers"],
                4)

            if fleetShipId == -1:
                #failed to assign ships for this exp, restore the ship pool
                Log.log_debug(f"ship_pool restore")
                ship_pool = ship_pool_bak 
            else:

                #Save the fleetShipId
                self.custom_presets["exp"][fleet_id] = fleetShipId
                exp.expedition.exp_for_fleet[fleet_id] = exp_rank["id"]

                fleet_id = self._get_next_exp_fleet_id(fleet_id)

            if fleet_id > 4:
                #assign for all fleets success
                break
            
        if fleet_id > 4:
            #assign for all fleets successed
            Log.log_success(f"auto mode asigned ship for exp{exp.expedition.exp_for_fleet[2:]}")
            return True
        else:
            #some assign failed
            return False

    def _assign_ship(self, fleet_list, ship_pool, req_dc=0, req_dc_carrier=0, req_lc=4):
        """
            Method to assign the ship with the given fleet_list and ship_pool

            input: 
                fleet_list: The ship type 
                    ex. [{'type': 'DD', 'id': 0}, 
                            {'type': 'DD', 'id': 1}, 
                            {'type': 'DD', 'id': 2}, 
                            {'type': 'DD', 'id': 3}, 
                            {'type': 'DD', 'id': 4}, 
                            {'type': 'DD', 'id': 5}]
                ship_pool(dict): The pool of ship to use
                    ex. {"DD":[10,20,30], "CL":[41,42,43]}
            
            output:
                -1: failed to assign a valid fleet
                ship_id(dict): the ship to use for the specified exp
                    (ex: [14,15,62,2,1,73]
            Note:
                This function should handle the wildcard("NA") type,
                so that the output here should not contain any "NA"
        """
        ship_id = []
        for ship in fleet_list:
            if ship['type'] == 'NA':
                #@todo: apply the wildcard handling
                ship['type'] = 'DD'

            wildcard = ".*"
            suffix = ship['type']
            pattern = rf"EXP_{wildcard}{suffix}"
            matching_keys = [key for key in ship_pool.keys() if re.match(pattern, key) and "NAME" not in key]

            pattern = r'\d+LC'  # Matches one or more digits followed by "LC"

            lc_temp_list = [[],[],[],[],[]]
            offset = 0
            for i in range(len(matching_keys)):

                match = re.search(pattern, matching_keys[i - offset])
                if match:
                    number = int(match.group()[:-2])

                    temp = matching_keys.pop(i - offset)

                    lc_temp_list[number].append(temp)
                    offset += 1
            
            if req_lc > 0:
                for i in range(1, req_lc):
                    for ship_type in lc_temp_list[i]:
                        matching_keys.insert(0, ship_type)

                for i in range(4, req_lc-1, -1):
                    for ship_type in lc_temp_list[i]:
                        matching_keys.insert(0, ship_type)

            pattern = r'\d+DC'  # Matches one or more digits followed by "DC"

            dc_temp_list = [[],[],[],[],[]]
            offset = 0
            for i in range(len(matching_keys)):
                match = re.search(pattern, matching_keys[i - offset])
                if match:
                    number = int(match.group()[:-2])

                    temp = matching_keys.pop(i - offset)

                    dc_temp_list[number].append(temp)
                    offset += 1
            
            if req_dc > 0 or req_dc_carrier > 0:
                for i in range(1, min(req_dc,5), 1):
                    for ship_type in dc_temp_list[i]:
                        matching_keys.insert(0, ship_type)

                for i in range(4, max(req_dc-1, 0), -1):
                    for ship_type in dc_temp_list[i]:
                        matching_keys.insert(0, ship_type)
            else:
                for i in range(1, 5):
                    for ship_type in dc_temp_list[i]:
                        matching_keys.append(ship_type)

            if req_lc <= 0:
                for i in range(1, 5):
                    for ship_type in lc_temp_list[i]:
                        matching_keys.append(ship_type)

            Log.log_debug(f"fleet_switcher_core: matching_keys = {matching_keys}")

            success = False
            for ship_type in matching_keys:

                Log.log_debug(f"fleet_switcher_core: searching for {ship_type}")
                Log.log_debug(f"len = {len(ship_pool[ship_type])}")
                if len(ship_pool[ship_type]) > 0:

                    ship_id.append(ship_pool[ship_type].pop(0))

                    pattern = r'\d+LC'  # Matches one or more digits followed by "LC"
                    match = re.search(pattern, ship_type)
                    if match:
                        number = int(match.group()[:-2])
                        req_lc -= number

                    pattern = r'\d+DC'  # Matches one or more digits followed by "DC"
                    match = re.search(pattern, ship_type)
                    if match:
                        number = int(match.group()[:-2])
                        req_dc -= number
                        req_dc_carrier -= 1

                    success = True
                    break
            
            if success == False: 
                #Cannot find a valid ship
                Log.log_debug(f"fleet_switcher_core: assign ship failed for {fleet_list}")
                return -1, ship_pool

        return ship_id, ship_pool

    def _get_next_exp_fleet_id(self, fleet_id):
        while 1:
            fleet_id+=1
            if fleet_id == 2:
                cur_fleet = cfg.config.expedition.fleet_2
            elif fleet_id == 3:
                cur_fleet = cfg.config.expedition.fleet_3
            elif fleet_id == 4:
                cur_fleet = cfg.config.expedition.fleet_4
            else:
                break

            if cur_fleet != []:
                break
        return fleet_id

    def _get_fleet_ship_type_from_composition(self, composition):
        """
            Convert the string composition (ex. "5DD, 1NA") to 
            fleetShipType (ex. [{'type': 'DD', 'id': None}, 
                            {'type': 'DD', 'id': None}, 
                            {'type': 'DD', 'id': None}, 
                            {'type': 'DD', 'id': None}, 
                            {'type': 'DD', 'id': None}, 
                            {'type': 'NA', 'id': None}])
        """
        fleetShipType = []

        for type in composition.split(","):
            count = int(type[:1])  # Extract the count from the substring
            item_type = type[1:]  # Extract the type from the substring

            for _ in range(count):
                fleetShipType.append({"type": item_type, "id": None})

        return fleetShipType
 
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
                    #if not self.switch_to_costom_equipment(combat_fleet_id, equipment_list):
                    self.switch_to_costom_equipment(equipment_key)
                    
                    nav.navigate.to('refresh_home')
                    self.goto()
                        
                    if not self.switch_to_costom_fleet(combat_fleet_id, fleet_list):
                        return False

                """Check if next combat possible, since new ship is switched in"""
                """Refresh home to update ship list"""
                com.combat.set_next_sortie_time(override=True)
                
            elif context == "pvp":
                Log.log_msg(f"Switching to PvP Preset.")

                fleet_list = self._get_fleet_preset("C-pvp")
                equipment_key = self._get_equipment_preset("C-pvp")
                
                self.switch_to_costom_equipment(equipment_key)
                    
                nav.navigate.to('refresh_home')
                self.goto()
                        
                if not self.switch_to_costom_fleet(1, fleet_list):
                    return False

            elif context == "expedition":
                Log.log_msg(f"Switching to Exp Preset.")

                if len(exp.expedition.fleets_at_base) < 3:
                    Log.log_error("Not all expedition fleets at base.")
                    return False
                    
                for fleet_id in range(2,5):

                    if fleet_id > 4:
                        break
                    
                    if not self.switch_to_costom_equipment(exp.expedition.exp_for_fleet[fleet_id]):
                        Log.log_error("Failed to switch equipment for expedition fleet.")
                        exit(1)
 
                nav.navigate.to('refresh_home')
                self.goto()
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
                    
                    temp = {}
                    temp[fleet_id] = flt.fleets.fleets[exp.expedition.exp_for_fleet[fleet_id]]
                    if not self.switch_to_costom_fleet(fleet_id, temp):
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
    
    def switch_to_costom_equipment(self, map_name):
        return equ.equipment.load_loaded_equipment(map_name)

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
