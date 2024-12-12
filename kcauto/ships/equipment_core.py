from datetime import datetime
from sys import exit
import api.api_core as api
import fleet_switcher.fleet_switcher_core as fsw
import ships.ships_core as shp
import ship_switcher.ship_switcher_core as ssw
import fleet.fleet_core as flt
import nav.nav as nav
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.fleet import FleetEnum
import util.kca as kca_u
from util.json_data import JsonData
from util.logger import Log
from util.wctf import WhoCallsTheFleetData
from fleet.noro6 import Noro6 
from fleet.fleet import Fleet
from random import randrange

class EquipmentCore(object):

    equipment = {}
    equipment_exp = {}  #contain all equipments which does not exist in noro6 config
    reinforce_general_category = {}
    reinforce_special = {}
    ship_type = []
    equipment_special = []
    
    custom_equipment = {}
    
    is_custom_fleet_equipment_loaded = False

    def __init__(self):
        self.equipment["raw"] = {}
        self.equipment["loaded"] = {}
        self.equipment["free"] = []
        self.equipment["id"] = {}

        try:
            self.reinforce_general_category = JsonData.load_json('data|temp|reinforce_general_category.json')
            self.reinforce_special = JsonData.load_json('data|temp|reinforce_special.json')
            self.ship_type = JsonData.load_json('data|temp|ship_type.json')
            self.equipment_special = JsonData.load_json('data|temp|equipment_ship_special.json')
        except FileNotFoundError:
            Log.log_error("Reinforce equipment data not found, please start kcauto from splash screen")

        try:
            self.equipment["id"] = JsonData.load_json('data|temp|equipment_list.json')
        except FileNotFoundError:
            Log.log_debug("Equipment data not found, use empty list instead")
            JsonData.dump_json(self.equipment["id"], 'data|temp|equipment_list.json')
    
    def fill_with_equipment(self, ship, equipment, count):
        """
            method to fill a ship with one type of equipment
            
            arg:
                ship (Ship): ship instance
                equipment (int): equipment type id
            
            output a kcauto format ship equipment list
        """
        
        ret = {}
        ret[ship.production_id] = []
        
        i=0
        count = min(count, ship.slot_num)
        
        for i in range(5):
            if count > 0:
                temp_equipment = self._get_production_id(self.equipment_exp, equipment)
                if temp_equipment == []:
                    ret[ship.production_id] = None
                    return
                ret[ship.production_id].append(temp_equipment[0])
                self._remove_from_pool(equipment_id=temp_equipment[0], equipment_pool=False, equipment_exp_pool=True)
                count -= 1
            else:
                ret[ship.production_id].append(-1)
            
        ret[ship.production_id].append(ship.slot_ex)
        
        return ret
            
    def _remove_from_pool(self, equipment_id, equipment_pool = True, equipment_exp_pool = False):
        
        if equipment_pool == True:
            for equipment in self.equipment["id"]:
                if equipment["api_id"] == equipment_id:
                    self.equipment["id"].remove(equipment)
                    break
                
        if equipment_exp_pool == True:
            for equipment in self.equipment_exp:
                if equipment["api_id"] == equipment_id:
                    self.equipment_exp.remove(equipment)
                    break
            
            
    def noro6_to_kcauto(self):
        """
            method to load the noro6 equipment list
            convert it to kcauto format and save it to a json file
            file_name (str): equipment config json file
            output (kcauto preset) :
        """
        
        equipment_bak = self.equipment["id"].copy()
        self.equipment_exp = self.equipment["id"].copy()
        
        ret = {}
        noro6 = Noro6()
 
        for preset in noro6.presets:
            noro6.get_map(preset["name"])
            ret[preset["name"]] = {}
           
            for fleet_id in range(1, noro6.get_fleet_count() + 1 ):
                noro6.get_fleet(fleet_id)
                
                for i in range(1, noro6.get_ship_count() + 1 ):
                    ship = shp.ships.get_ship_from_noro6_ship(noro6.get_ship(i))
                    ret[preset["name"]][ship.production_id] = []
                    
                    for j in range(1, noro6.get_equipment_count() + 1 ):
                        
                        this_equipment = self._get_equipment_from_noro6_equipment(noro6.get_equipment(j))
                        ret[preset["name"]][ship.production_id].append(
                            this_equipment["api_id"]
                        )
                        
                        #remove this equipment from equipment pool
                        self._remove_from_pool(equipment_id=this_equipment["api_id"], equipment_exp_pool=True)
                        
                    #padding to 6 equipment slot with -1
                    for k in range(noro6.get_equipment_count() + 1, 7):
                        ret[preset["name"]][ship.production_id].append(-1)
                   
                    
                    reinforce_equipment = noro6.get_reinforce_equipment()
                    if reinforce_equipment["i"] > 0:
                        this_equipment = self._get_equipment_from_noro6_equipment(reinforce_equipment)
                        ret[preset["name"]][ship.production_id][6-1] = this_equipment["api_id"]
                    
                        #remove this equipment from equipment pool
                        for equipment in self.equipment["id"]:
                            if equipment["api_id"] == this_equipment["api_id"]:
                                self.equipment["id"].remove(equipment)
                                break
                    else:
                        ret[preset["name"]][ship.production_id][6-1] = reinforce_equipment["i"]

                        
                        
            self.equipment["id"] = equipment_bak.copy()                    
                
        return ret 
    
    def _get_equipment_from_noro6_equipment(self, noro6_equipment):
        """
            method to convert noro6 equipment to kcauto equipment
            noro6_equipment (dict): noro6 equipment data
            output (int) : equipment production id
        """
        production_id_list = self._get_production_id(self.equipment["id"], noro6_equipment["i"])
       
        is_any_match = False
        temp_equipment = []
        for id in production_id_list:
            for equipment in self.equipment["id"]:
                if equipment["api_id"] == id:
                    is_any_match = True
                    temp_equipment.append(equipment)
                    
        if is_any_match == False:
            Log.log_error("can't find any match equipment")
            return None
        
        for i in range(len(temp_equipment)):
            
            #@todo handle "api_alv"/"l" (plane exp level)
            #if "api_alv" in temp_equipment[i] and "l" in noro6_equipment:
            if temp_equipment[i]["api_level"] == noro6_equipment["r"]:
                return temp_equipment[i]
            
        if len(temp_equipment) == 0:
            Log.log_error("can't find any match equipment")
            return None
        
        #sort by the absolute value of difference between api_lv and rf
        temp_equipment.sort(key=lambda x: abs(x["api_level"] - noro6_equipment["r"]))
        #@todo send warring, can't find exact same equipment

        return temp_equipment[0]
        
 
    def get_loaded_equipment(self, api_data):
        """
            method to read the loaded equipment list from api data 

            api_data (dict) : data from "port/api_data/api_ship" api
        """
        self.equipment["loaded"] = {}
        
        for ship in api_data:
            self.equipment["loaded"][ship['api_id']] = ship["api_slot"]
            self.equipment["loaded"][ship['api_id']].append(ship["api_slot_ex"])


    def unload_equipment(self, map_name):
        """
            method to load the loaded equipment list from a json file
            file_name (str): equipment config json file
        """
        
        any_unload = False

        EMPTY_a = [-1,-1,-1,-1,-1,0]
        EMPTY_b = [-1,-1,-1,-1,-1,-1]

        nav.navigate.to('refresh_home')

        target_config = self.custom_equipment[map_name]
            
        unload_ship_id = []

        for ship_id in self.equipment["loaded"]:
            
            if ship_id in target_config:
                if self.equipment["loaded"][ship_id] != target_config[ship_id]\
                    and self.equipment["loaded"][ship_id] != EMPTY_a\
                    and self.equipment["loaded"][ship_id] != EMPTY_b:
                    unload_ship_id.append(ship_id)
                    any_unload = True
            else: #target_config does not care this ship, but we still have to strip it if it holds any equipment we care
                
                if  self.equipment["loaded"][ship_id] != EMPTY_a\
                and self.equipment["loaded"][ship_id] != EMPTY_b:
                    
                    target_equipments = set()
                    
                    for equipment_list in target_config.values():
                        target_equipments.update(equipment_list)
                        
                    target_equipments.discard(0)
                    target_equipments.discard(-1)
                        
                    for euipment in self.equipment["loaded"][ship_id]:
                        if euipment in target_equipments:
                            unload_ship_id.append(ship_id)
                            any_unload = True
                            break

        needed_load = False
        if any_unload == True:
            #@todo temp element repeat fix
            unload_ship_id = list(set(unload_ship_id))
        else:
            for ship_id in self.equipment["loaded"]:
                try:
                    if      target_config[ship_id] == EMPTY_a\
                        or  target_config[ship_id] == EMPTY_b:
                        #nothing to load
                        continue

                    if self.equipment["loaded"][ship_id] != target_config[ship_id]:
                        Log.log_error(f'ship {ship_id} currently has {self.equipment["loaded"][ship_id]}, target is {target_config[ship_id]}')
                        needed_load = True
                        break
                        
                except KeyError:
                    pass

            if needed_load == True: 
                #let the current secretary ship load and unload a whatever equipment
                unload_ship_id = [flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][1].ship_ids[0]]
        
        start_id = 0
        while len(unload_ship_id) > start_id:
            
            fleet_size = min(6, len(unload_ship_id) - start_id)
            
            if needed_load == False:
                fsw.fleet_switcher.goto()
                
                temp_fleet = {}
                temp_fleet[1]=(Fleet("unload_equipment", FleetEnum.COMBAT, False))
                temp_fleet[1].ship_data = []
                for i in range(0, fleet_size):
                    temp_fleet[1].ship_data.append(
                        shp.ships.get_ship_from_production_id(unload_ship_id[start_id + i])
                    )
                if not fsw.fleet_switcher.switch_to_costom_fleet(1, temp_fleet):
                    Log.log_error("kcauto failed to load the selected ship, exiting...")
                    break

            nav.navigate.to('equipment')

            for i in range(fleet_size):
            
                Log.log_debug(f"unload the {i+1} ship")
                kca_u.kca.click('ship_'+ str(i + 1)) 
                
                if needed_load == True:
                    #unload a ship to update equipment list
                    Log.log_error("Load and unload a whatever equipment to update equipment api")
                    kca_u.kca.click('1_slot_equipment') 
                    
                    ssw.ship_switcher.select_replacement_row(row_idx=randrange(10), mode= "equipment")

                    kca_u.kca.click_existing(
                        'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')
                    kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                    api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True, timeout=30)
                
                while True:
                    if kca_u.kca.exists('equipment_panel', 'shipswitcher|1_slot_ship.png'):
                        Log.log_debug(f"1 slot ship")
                        kca_u.kca.click('1_slot_unload_equipment')
                    elif kca_u.kca.exists('equipment_panel', 'shipswitcher|2_slot_ship.png',cached=True):
                        Log.log_debug(f"2 slot ship")
                        kca_u.kca.click('2_slot_unload_equipment') 
                    elif kca_u.kca.exists('equipment_panel', 'shipswitcher|3_slot_ship.png',cached=True):
                        Log.log_debug(f"3 slot ship")
                        kca_u.kca.click('3_slot_unload_equipment') 
                    elif kca_u.kca.exists('equipment_panel', 'shipswitcher|4_slot_ship.png',cached=True):
                        Log.log_debug(f"4 slot ship")
                        kca_u.kca.click('4_slot_unload_equipment') 
                    else: 
                        Log.log_debug(f"5 slot ship")
                        kca_u.kca.click('5_slot_unload_equipment') 

                    kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                    
                    if self.equipment["loaded"][unload_ship_id[start_id + i]][-1] > 0:
                        Log.log_debug(f"reinforce slot ship")
                        kca_u.kca.click('reinforce_slot_unload_equipment') 

                    kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                    
                    api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True, timeout=5)
                    if api_result != {}:
                        break
                    Log.log_debug(f"catched, not receiving equipment update api")
                    
            start_id += fleet_size

        return any_unload

    def load_equipment(self, fleet_id, fleet, map_name):

        EMPTY_a = [-1,-1,-1,-1,-1,0]
        EMPTY_b = [-1,-1,-1,-1,-1,-1]

        nav.navigate.to('home')

        target_config = self.custom_equipment[map_name]
        Log.log_debug("load_equipment target_config")
        Log.log_debug(target_config)

        load_ship_id = fleet
        """
        for ship_id in self.equipment["loaded"]:
            try:
                if      target_config[ship_id] == EMPTY_a\
                    or  target_config[ship_id] == EMPTY_b:
                    #nothing to load
                    continue

                if self.equipment["loaded"][ship_id] != target_config[ship_id]:
                    # at this point, every ship doesn't have the target equipment should get unloaded already
                    load_ship_id.append(ship_id)
            except KeyError:
                pass
        """

        fleet_size = len(load_ship_id)
        nav.navigate.to('equipment')
        
        
        kca_u.kca.wait("left", f"nav|side_menu_equipment_active.png")
        while True:
            Log.log_error(f"click on fleet {fleet_id}")
            kca_u.kca.click_existing("upper_left", f"fleet|fleet_{fleet_id}.png")
            if  kca_u.kca.exists("upper_left", f"fleet|fleet_{fleet_id}_active.png"):
                break
            kca_u.kca.sleep(1)
        Log.log_error(f"switched to {fleet_id}")
        
            
        for i in range(fleet_size):

            if load_ship_id[i] not in target_config:
                continue
            elif self.equipment["loaded"][load_ship_id[i]] == target_config[load_ship_id[i]]:
                Log.log_error(f"equipment for ship {load_ship_id[i]} is already loaded")
                continue
            
            Log.log_debug(f"load the {i+1} ship")
            kca_u.kca.click('ship_'+ str(i + 1)) 

            ssw.ship_switcher.current_page = 1
            for slot in range(1,7):

                equipment_id = target_config[load_ship_id[i]][slot - 1]
                if equipment_id == -1 or equipment_id == 0:
                    continue

                if slot < 6:
                    kca_u.kca.click(str(slot) + '_slot_equipment') 

                    if slot == 1:
                        kca_u.kca.click_existing('upper_right', 'shipswitcher|equipment_sort_arrow.png')
                        kca_u.kca.click('equipment_sort_all')
                    
                    kca_u.kca.wait('upper_right', 'shipswitcher|equipment_sort_all.png')
                else:
                    kca_u.kca.click('reinforce_slot_equipment') 

                try:
                    if slot < 6:
                        row_id = self.equipment["free"].index(equipment_id)
                    else:
                        row_id = self.get_reinforce_equipment_list(load_ship_id[i]).index(equipment_id)
                        ssw.ship_switcher.current_page = 1
                except ValueError:
                    Log.log_error(f"Cannot find equipment name id:{self._get_name_id(equipment_id)} production id:{equipment_id}, did you scrapped it?")
                    exit(1)

                ssw.ship_switcher.select_replacement_row(row_idx=row_id, mode= "equipment")

                kca_u.kca.click_existing(
                    'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')
                kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True, timeout=30)

        return True

    def get_reinforce_equipment_list(self, local_id):

        
        equipment_list = []

        ship = shp.ships.get_ship_from_production_id(local_id)
        special_equipment_list = self.get_special_reinforce_equipment(ship) # sqecial equipment for this ship only

        keys = self.equipment['raw'].keys()
        sorted_keys = sorted(keys, key=lambda x: (len(x), x))
        Log.log_debug(sorted_keys)

        for key in sorted_keys:
            #key is always "api_slottypeXXX"
            Log.log_debug(key)
            Log.log_debug(self.equipment['raw'][key])
            if      int(key[12:]) in self.reinforce_general_category \
                and self.is_available_category(ship, int(key[12:])):
                equipment_list = equipment_list + self.equipment['raw'][key]
            else:
                # see if this category has any special reinforce equipment
                for production_id in self.equipment['raw'][key]:
                    name_id = self._get_name_id(production_id)
                    if name_id in special_equipment_list:
                        equipment_list.append(production_id)
                        Log.log_debug("hit")


        Log.log_debug("equipment_list")
        Log.log_debug(equipment_list)

        return equipment_list

    def get_special_reinforce_equipment(self, ship):

        WILDCARD_SHIP_TYPE = "99"

        equipment_list = []

        Log.log_debug(type(ship.api_id))
        Log.log_debug(ship.api_id)
        Log.log_debug(type(ship.ship_family))
        Log.log_debug(ship.ship_family)
        Log.log_debug(type(ship.ship_type.id))
        Log.log_debug(ship.ship_type.id)
        
        Log.log_debug(self.reinforce_special)

        for key in self.reinforce_special:
            if \
                (self.reinforce_special[key]["api_ship_ids"] is not None \
                and \
                str(ship.api_id) in self.reinforce_special[key]["api_ship_ids"].keys())\
            or \
                (self.reinforce_special[key]["api_ctypes"] is not None \
                and \
                str(ship.ship_family) in self.reinforce_special[key]["api_ctypes"].keys())\
            or \
                (self.reinforce_special[key]["api_stypes"] is not None \
                and \
                    (str(ship.ship_type.id) in self.reinforce_special[key]["api_stypes"].keys() \
                        or\
                    WILDCARD_SHIP_TYPE in self.reinforce_special[key]["api_stypes"].keys())):
                Log.log_debug("hit")
                equipment_list.append(int(key))


        Log.log_debug("special equipment_list")
        Log.log_debug(equipment_list)

        return equipment_list

    def _get_name_id(self, production_id):
        """method to convert equipment production id to equipment name id"""

        for id in self.equipment["id"]:
            if id["api_id"] == production_id:
                return id["api_slotitem_id"]        
        Log.log_warn(f"Cannot find production_id:{production_id} in equipment list, performing sortie to update")
        return None

    def _get_production_id(self, equipment_pool, name_id):
        """method to convert equipment name id to equipment production id list"""
        
        is_any_match = False
        output_list = []

        for id in equipment_pool:
            if id["api_slotitem_id"] == name_id:
                output_list.append(id["api_id"])
                is_any_match = True

        if is_any_match != True:
            Log.log_warn(f"Cannot find namd_id:{name_id} in equipment list, looks like you don't have any")

        return output_list

    def is_available_category(self, target_ship, category_id):

        # If this ship has a special available equipment category
        ship_id = target_ship.api_id
        for ship in self.equipment_special:
            if ship["api_ship_id"] == ship_id:
                if category_id in ship["api_equip_type"]:
                    return True
                else:
                    return False

        # If this ship use general equipment category
        type_id = target_ship.ship_type.id
        for ship in self.ship_type:
            if ship["api_id"] == type_id:
                if ship["api_equip_type"][str(category_id)] == 1:
                    return True
                else:
                    return False

        Log.log_warn(f"Cannot find ship type id:{type_id}")
        return False

equipment = EquipmentCore()
