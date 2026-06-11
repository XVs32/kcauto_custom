from ships.ship import Ship
from util.json_data import JsonData
from util.logger import Log
from util.wctf import WhoCallsTheFleetData


class ShipsCore(object):
    max_ship_count = 0
    ship_pool: dict[int, Ship] = {}
    ship_library = []
    name_db = {}

    def __init__(self):
        Log.log_debug_1("Initializing Ship core.")
        self.load_wctf_names()

    def update_ship_pool(self, data):
        # from this api call, api_id = local_api_id, and api_ship_id = api_id
        Log.log_debug_1("Updating ship data from API.")
        self.ship_pool = {}
        for ship in data:
            self.ship_pool[ship["api_id"]] = self.create_ship(
                self.get_ship_static_data(ship["api_sortno"]), ship
            )

    def update_ship_library(self, data):
        Log.log_debug_1("Updating ship library data.")
        self.ship_library = data

    def is_ship_pool_full(self, is_event=False):
        """check if ship pool is full

        Args:
            is_event (bool, optional): whether in event mode, event require 5 more free slots then usual. Defaults to False.
        Returns:
            bool: True if ship pool is full, False otherwise
        """
        required_free_slots = 5 if is_event else 0
        return len(self.ship_pool) >= (self.max_ship_count - required_free_slots)

    def get_ship_static_data(self, api_sortno, api_id=None):
        """get ship static data from ship library with api_sortno or api_id

        Args:
            api_sortno (int): Picture book number of the ship
            api_id (int, optional): model id of the ship. Defaults to None.

        Returns:
            ship static data (dict): ship static data from ship library, return none if not found
        """

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
            temp_db = JsonData.load_json("data|temp|wctf.json")
        except FileNotFoundError:
            WhoCallsTheFleetData.get_and_save_wgtf_data()
            temp_db = JsonData.load_json("data|temp|wctf.json")

        self.name_db = {}
        for key in temp_db:
            self.name_db[int(key)] = temp_db[key]

    @property
    def ship_count(self):
        return len(self.ship_pool)

    def get_ship_from_production_id(self, ship_id) -> Ship:

        if ship_id == 0:
            Log.log_debug_2("Ship id 0 is requested.")
            return None

        if ship_id not in self.ship_pool:
            Log.log_error(f"Ship #{ship_id} not found in port.")
            return None

        return self.ship_pool[ship_id]

    def get_highest_level_ship_by_type(self, ship_type) -> Ship:
        ships_of_type = [s for s in self.ship_pool.values() if s.ship_type == ship_type]
        if not ships_of_type:
            Log.log_error(f"No ships of type {ship_type.display_name} found in port.")
            return None
        return max(ships_of_type, key=lambda s: s.level)

    def create_ship(self, static_data, local_data=Ship.EMPTY_LOCAL_DATA):
        return Ship(static_data, local_data)

    def get_ship_from_noro6_ship(self, noro_ship):
        """
        method to find the most match ship in ship_pool from noro6 ship info
        input: noro6 ship info
        output: kcauto ship obj
        """

        ret = self.get_ship_from_production_id(noro_ship.get("un", 0))

        if ret is None:
            static_data = self.get_ship_static_data(None, api_id=noro_ship["i"])

            ship_name = static_data["api_name"] if static_data else "Unknown"

            Log.log_error(
                f"Ship {ship_name} #{noro_ship.get('i', 'Unknown')} not found in ship pool, exiting..."
            )

        return ret

    def is_same_ship(self, ship1: Ship, ship2: Ship):
        if ship1 is None or ship2 is None:
            return False
        return ship1.production_id == ship2.production_id


ships = ShipsCore()
