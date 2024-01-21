from datetime import datetime
import fleet_switcher.fleet_switcher_core as fsw
import util.kca as kca_u
from util.json_data import JsonData
from util.logger import Log
from util.wctf import WhoCallsTheFleetData
import nav.nav as nav

class EquipmentCore(object):

    equipment = {}

    def __init__(self):
        self.equipment["loaded"] = {}
        self.equipment["free"] = {}

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
        """
            method to load the loaded equipment list from a json file
            file_name (str): equipment config json file
        """

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
            except KeyError:
                if self.equipment["loaded"][ship_id] != EMPTY_a\
                and self.equipment["loaded"][ship_id] != EMPTY_b:
                    unload_ship_id.append(ship_id)

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

            start_id += fleet_size

        exit(0)






equipment = EquipmentCore()
