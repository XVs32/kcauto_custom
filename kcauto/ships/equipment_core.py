from datetime import datetime
from sys import exit
import api.api_core as api
import fleet_switcher.fleet_switcher_core as fsw
import ships.ships_core as shp
import ship_switcher.ship_switcher_core as ssw
import fleet.fleet_core as flt
import nav.nav as nav
from kca_enums.kcsapi_paths import KCSAPIEnum
import util.kca as kca_u
from util.json_data import JsonData
from util.logger import Log
from util.wctf import WhoCallsTheFleetData
from fleet.noro6 import Noro6 

class EquipmentCore(object):

    equipment = {}
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
            
    def _noro6_to_kcauto(self, file_path):
        """
            method to load the noro6 equipment list
            convert it to kcauto format and save it to a json file
            file_name (str): equipment config json file
            output (kcauto preset) :
        """
        
        ret = {}
        noro6 = Noro6(file_path)
 
        for fleet_id in range(1, noro6.get_fleet_count() + 1 ):
            noro6.get_fleet(fleet_id)
            
            for i in range(1, noro6.get_ship_count() + 1 ):
                ship = shp.ships.get_ship_from_noro6_ship(noro6.get_ship(i))
                ret[ship.production_id] = []
                
                for j in range(1, noro6.get_equipment_count() + 1 ):
                    ret[ship.production_id].append(
                        self._get_equipment_from_noro6_equipment(noro6.get_equipment(j))
                    )
                
        return ret 
    
    def _get_equipment_from_noro6_equipment(self, noro6_equipment):
        """
            method to convert noro6 equipment to kcauto equipment
            noro6_equipment (dict): noro6 equipment data
            output (kcauto equipment) :
        """
        production_id_list = self._get_production_id(noro6_equipment["id"])
       
        temp_equipment = []
        for id in production_id_list:
            for equipment in self.equipment["id"]:
                if equipment["api_id"] == id:
                    temp_equipment.append(equipment)
                    break
            
        
        for i in range(len(temp_equipment)-1,-1,-1):
            
            #@todo handle "api_alv"/"mas" (plane exp level)
            #if "api_alv" in temp_equipment[i] and "mas" in noro6_equipment:
            if temp_equipment[i]["api_level"] == noro6_equipment["rf"]:
                return temp_equipment[i]
            
        #sort by the absolute value of difference between api_lv and rf
        temp_equipment.sort(key=lambda x: abs(x["api_lv"] - noro6_equipment["rf"]))

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

    def save_fleet_equipment(self, fleet_id):
        """
            method to read the loaded equipment list of a fleet

            fleet_id (dict) : fleet id, starts from 1
        """
        
        print (flt.fleets.fleets[fleet_id].ship_ids)
        
        equipment_list = {}
        
        for ship_id in flt.fleets.fleets[fleet_id].ship_ids:
            equipment_list[ship_id] = self.equipment["loaded"][ship_id]
            
        
        dt_string = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        JsonData.dump_json(equipment_list, 'data|equipment|' + dt_string + '.json')
            
        Log.log_success(f"Equipment list saved at data/equipment/{dt_string}.json")
        
        
        Log.log_error(f"this function is temp disabled.") 
        exit(1)
            

    def save_loaded_equipment(self):
        """
            method to save the loaded equipment list to a json file
        """
        
        nav.navigate.to('refresh_home')

        dt_string = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        JsonData.dump_json(self.equipment["loaded"], 'data|equipment|' + dt_string + '.json')

        Log.log_success(f"Equipment list saved at data/equipment/{dt_string}.json")

        exit(0)

    def load_loaded_equipment(self, file_name):
        """
            method to load the equipment ref from json file
        """
        
        print("load in")
        
        if not self.unload_equipment(file_name):
            #@todo if no equipment is unloaded, load/upload whatever to update the equipment list
            #self.equipment_list_update()
            pass

        self.load_equipment(file_name)



    def unload_equipment(self, file_name):
        """
            method to load the loaded equipment list from a json file
            file_name (str): equipment config json file
        """
        
        any_unload = False

        EMPTY_a = [-1,-1,-1,-1,-1,0]
        EMPTY_b = [-1,-1,-1,-1,-1,-1]

        nav.navigate.to('refresh_home')

        target_config = JsonData.load_json('data|equipment|' + file_name + '.json')
        Log.log_debug(target_config)

        unload_ship_id = []

        for ship_id in self.equipment["loaded"]:
            
            if str(ship_id) in target_config:
                if self.equipment["loaded"][ship_id] != target_config[str(ship_id)]\
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

        start_id = 0
        while len(unload_ship_id) > start_id:
            fsw.fleet_switcher.goto()

            fleet_size = min(6, len(unload_ship_id) - start_id)
            if not fsw.fleet_switcher.switch_to_costom_fleet(1, unload_ship_id[start_id:start_id+fleet_size]):
                Log.log_error("kcauto failed to load the selected ship, exiting...")
                break


            nav.navigate.to('equipment')

            for i in range(fleet_size):
            
                Log.log_debug(f"unload the {i+1} ship")
                kca_u.kca.click('ship_'+ str(i + 1)) 

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

            start_id += fleet_size

        return any_unload

    def load_equipment(self, file_name):

        EMPTY_a = [-1,-1,-1,-1,-1,0]
        EMPTY_b = [-1,-1,-1,-1,-1,-1]

        nav.navigate.to('refresh_home')

        target_config = JsonData.load_json('data|equipment|' + file_name + '.json')
        Log.log_debug(target_config)

        load_ship_id = []

        for ship_id in self.equipment["loaded"]:
            try:
                if      target_config[str(ship_id)] == EMPTY_a\
                    or  target_config[str(ship_id)] == EMPTY_b:
                    #nothing to load
                    continue

                if self.equipment["loaded"][ship_id] != target_config[str(ship_id)]:
                    # at this point, every ship doesn't have the target equipment should get unloaded already
                    load_ship_id.append(ship_id)
            except KeyError:
                pass

        start_id = 0
        while len(load_ship_id) > start_id:
            fsw.fleet_switcher.goto()

            fleet_size = min(6, len(load_ship_id) - start_id)
            if not fsw.fleet_switcher.switch_to_costom_fleet(1, load_ship_id[start_id:start_id+fleet_size]):
                Log.log_error("kcauto failed to load the selected ship, exiting...")
                break

            nav.navigate.to('equipment')

            for i in range(fleet_size):

                Log.log_debug(f"unload the {i+1} ship")
                kca_u.kca.click('ship_'+ str(i + 1)) 

                ssw.ship_switcher.current_page = 1
                for slot in range(1,7):

                    equipment_id = target_config[str(load_ship_id[start_id + i])][slot - 1]
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
                            row_id = self.get_reinforce_equipment_list(load_ship_id[start_id + i]).index(equipment_id)
                            ssw.ship_switcher.current_page = 1
                    except ValueError:
                        Log.log_error(f"Cannot find equipment {equipment_id}, did you scrapped it?")
                        continue

                    ssw.ship_switcher.select_replacement_row(row_idx=row_id, mode= "equipment")

                    kca_u.kca.click_existing(
                        'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')
                    kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                    api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True, timeout=30)


            start_id += fleet_size



        Log.log_debug(load_ship_id)
        exit(0)

    def get_reinforce_equipment_list(self, local_id):

        Log.log_debug("equipment_list")
        
        equipment_list = []

        ship = shp.ships.local_ships_by_production_id[local_id]
        special_equipment_list = self.get_special_reinforce_equipment(ship) # sqecial equipment for this ship only

        keys = self.equipment['raw'].keys()
        sorted_keys = sorted(keys, key=lambda x: (len(x), x))
        Log.log_debug(sorted_keys)

        for key in sorted_keys:
            #key is always "api_slottypeXXX"
            Log.log_debug(key)
            Log.log_debug(self.equipment['raw'][key])
            if      int(key[12:]) in self.reinforce_general_category \
                and self._is_available_category(ship, int(key[12:])):
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

    def _get_production_id(self, name_id):
        """method to convert equipment name id to equipment production id list"""
        
        is_any_match = False
        output_list = []

        for id in self.equipment["id"]:
            if id["api_slotitem_id"] == name_id:
                output_list.append(id["api_id"])
                is_any_match = True

        if is_any_match == True:
            Log.log_warn(f"Cannot find namd_id:{name_id} in equipment list, looks like you don't have any")

        return output_list

    def _is_available_category(self, target_ship, category_id):

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
