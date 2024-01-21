from datetime import datetime
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

equipment = EquipmentCore()
