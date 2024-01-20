from util.json_data import JsonData
from util.logger import Log
from util.wctf import WhoCallsTheFleetData

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
            Log.log_debug(f"ship {ship['api_id']} equipment")
            Log.log_debug(ship["api_slot"])
            Log.log_debug(ship["api_slot_ex"])
            self.equipment["loaded"][ship['api_id']] = ship["api_slot"]
            self.equipment["loaded"][ship['api_id']].append(ship["api_slot_ex"])
        Log.log_debug(self.equipment["loaded"])

equipment = EquipmentCore()
