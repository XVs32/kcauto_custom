from ships.ship import Ship
from util.json_data import JsonData
from util.logger import Log
from util.wctf import WhoCallsTheFleetData


class ShipsCore(object):
    max_ship_count = 0
    ship_pool = []
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
            ship_instance = self.get_ship_from_api_id(
                ship['api_ship_id'], ship)
            self.ship_pool[ship['api_id']] = ship_instance
            
        print("self.ship_pool")
        print(self.ship_pool)
        exit()

    def update_ship_library(self, data):
        Log.log_debug("Updating ship library data.")
        self.ship_library = data

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
    def current_ship_count(self):
        return len(self.ship_pool)

    def get_ship_with_production_id(self, req_ships):
        """get ship obj with a list of ship production id

        Args:
            req_ships (list of int): a list of ship production id

        Returns:
            ships: list of ship obj
        """
        
        ships = []
        for production_id in req_ships:
            ships.append(self.local_ships_by_production_id[production_id])
        return ships
    
    def get_ship_from_production_id(self, ship_id):
        return self.ship_pool[ship_id]

    def get_ship_from_api_id(self, api_id, local_ship_data=None):
        return Ship(api_id, local_data=local_ship_data)

    def get_ship_from_sortno(self, sortno):
        return Ship(sortno, id_type='sortno')


ships = ShipsCore()
