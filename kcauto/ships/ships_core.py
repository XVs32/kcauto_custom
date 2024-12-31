from ships.ship import Ship
from util.json_data import JsonData
from util.logger import Log
from util.wctf import WhoCallsTheFleetData


class ShipsCore(object):
    max_ship_count = 0
    ship_pool = {}
    local_ships_by_production_id = {}
    ship_library = []
    name_db = {}

    def __init__(self):
        Log.log_debug("Initializing Ship core.")
        self.load_wctf_names()

    def update_ship_pool(self, data):
        # from this api call, api_id = local_api_id, and api_ship_id = api_id
        Log.log_debug("Updating ship data from API.")
        self.ship_pool = {}
        for ship in data:
            ship_instance = self.create_ship(
                self.get_ship_static_data(ship["api_sortno"]), ship)
            self.ship_pool[ship['api_id']] = ship_instance
            

    def update_ship_library(self, data):
        Log.log_debug("Updating ship library data.")
        self.ship_library = data
        
    def get_ship_static_data(self,api_sortno, api_id = None):
        
        search_key = "api_sortno"
        id = api_sortno
        
        if api_id != None:
            id = api_id
            search_key = "api_id"
        
        for ship in self.ship_library:
            if search_key not in ship:
                continue
            
            if ship[search_key] == id:
                return ship

    def load_wctf_names(self, force_update=False):
        if force_update:
            WhoCallsTheFleetData.get_and_save_wgtf_data()

        try:
            temp_db = JsonData.load_json('data|temp|wctf.json')
        except FileNotFoundError:
            WhoCallsTheFleetData.get_and_save_wgtf_data()
            temp_db = JsonData.load_json('data|temp|wctf.json')

        self.name_db = {}
        for key in temp_db:
            self.name_db[int(key)] = temp_db[key]

    @property
    def ship_count(self):
        return len(self.ship_pool)

    def get_ship_from_production_id(self, ship_id):
        
        if ship_id not in self.ship_pool:
            Log.log_error(f"Ship #{ship_id} not found in port.")
            return None
        
        return self.ship_pool[ship_id]

    def create_ship(self, static_data, local_data = Ship.EMPTY_LOCAL_DATA):
        return Ship(static_data, local_data)
     
    def get_ship_from_noro6_ship(self, noro_ship):
        """
            method to find the most match ship in ship_pool from noro6 ship info
            input: noro6 ship info
            output: kcauto ship obj
        """
        ret = self.get_ship_from_production_id(noro_ship["un"])
        if ret == None:
            Log.log_error(f"Ship {self.get_ship_static_data(None, api_id=noro_ship['i'])['api_name']} #{noro_ship['i']} not found in ship pool, exiting...")
            
        return ret

ships = ShipsCore()
