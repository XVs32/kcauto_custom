from datetime import datetime
import api.api_core as api
import fleet_switcher.fleet_switcher_core as fsw
import ships.ships_core as shp
import ship_switcher.ship_switcher_core as ssw
import nav.nav as nav
from kca_enums.kcsapi_paths import KCSAPIEnum
import util.kca as kca_u
from util.json_data import JsonData
from util.logger import Log
from util.wctf import WhoCallsTheFleetData

class EquipmentCore(object):

    equipment = {}
    reinforce_general_category = {}
    reinforce_special = {}

    def __init__(self):
        self.equipment["raw"] = {}
        self.equipment["loaded"] = {}
        self.equipment["free"] = []
        self.equipment["id"] = {}

        try:
            self.reinforce_general_category = JsonData.load_json('data|temp|reinforce_general_category.json')
            self.reinforce_special = JsonData.load_json('data|temp|reinforce_special.json')
        except FileNotFoundError:
            Log.log_error("Reinforce equipment data not found, please start kcauto from splash screen")

        try:
            self.equipment["id"] = JsonData.load_json('data|temp|equipment_list.json')
        except FileNotFoundError:
            Log.log_debug("Equipment data not found, use empty list instead")
            JsonData.dump_json(self.equipment["id"], 'data|temp|equipment_list.json')
            

    def get_loaded_equipment(self, api_data):
        """
            method to read the loaded equipment list from api data 

            api_data (dict) : data from "port/api_data/api_ship" api
        """
        self.equipment["loaded"] = {}
        
        for ship in api_data:
            self.equipment["loaded"][ship['api_id']] = ship["api_slot"]
            self.equipment["loaded"][ship['api_id']].append(ship["api_slot_ex"])


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
        if not self.unload_equipment(file_name):
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
            try:
                if self.equipment["loaded"][ship_id] != target_config[str(ship_id)]\
                    and self.equipment["loaded"][ship_id] != EMPTY_a\
                    and self.equipment["loaded"][ship_id] != EMPTY_b:
                    unload_ship_id.append(ship_id)
                    any_unload = True
            except KeyError:
                if self.equipment["loaded"][ship_id] != EMPTY_a\
                and self.equipment["loaded"][ship_id] != EMPTY_b:
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
                    if equipment_id == -1:
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
        exit()

    def get_reinforce_equipment_list(self, local_id):

        Log.log_debug("equipment_list")
        
        equipment_list = []

        ship = shp.ships.local_ships_by_local_id[local_id]
        special_equipment_list = self.get_special_reinforce_equipment(local_id) # sqecial equipment for this ship only

        keys = self.equipment['raw'].keys()
        sorted_keys = sorted(keys, key=lambda x: (len(x), x))
        Log.log_debug(sorted_keys)

        for key in sorted_keys:
            #key is always "api_slottypeXXX"
            if int(key[12:]) in self.reinforce_general_category:
                equipment_list = equipment_list + self.equipment['raw'][key]
            else:
                # see if this category has any special reinforce equipment
                Log.log_debug("test1")
                Log.log_debug(key)
                Log.log_debug(self.equipment['raw'][key])
                for production_id in self.equipment['raw'][key]:
                    name_id = self._get_name_id(production_id)
                    if name_id in special_equipment_list:
                        equipment_list.append(production_id)
                        Log.log_debug("hit")


        Log.log_debug("equipment_list")
        Log.log_debug(equipment_list)

        return equipment_list

    def get_special_reinforce_equipment(self, local_id):

        equipment_list = []

        ship = shp.ships.local_ships_by_local_id[local_id]
        Log.log_debug(type(ship.api_id))
        Log.log_debug(ship.api_id)
        Log.log_debug(type(ship.ship_family))
        Log.log_debug(ship.ship_family)
        Log.log_debug(type(ship.ship_type.id))
        Log.log_debug(ship.ship_type.id)
        
        Log.log_debug(self.reinforce_special)

        for key in self.reinforce_special:
            if (self.reinforce_special[key]["api_ship_ids"] is not None \
            and str(ship.api_id) in self.reinforce_special[key]["api_ship_ids"].keys())\
            or (self.reinforce_special[key]["api_ctypes"] is not None \
            and str(ship.ship_family) in self.reinforce_special[key]["api_ctypes"].keys())\
            or (self.reinforce_special[key]["api_stypes"] is not None \
            and str(ship.ship_type.id) in self.reinforce_special[key]["api_stypes"].keys()):
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

equipment = EquipmentCore()
