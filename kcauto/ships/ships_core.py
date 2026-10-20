from ships.ship import Ship
from util.json_data import JsonData
from util.logger import Log
from util.wctf import WhoCallsTheFleetData
from constants import ENEMY_SHIP_API_ID_START

class ShipsCore(object):
    max_ship_count = 0
    ship_pool: dict[int, Ship] = {}
    ship_library = []
    ship_family_ids: dict[int, int] = {}
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
        self._update_ship_family_ids()

    def _update_ship_family_ids(self):
        # exclude enemy ship
        ships_by_id = {
            ship["api_id"]: ship
            for ship in self.ship_library
            if ship["api_id"] < ENEMY_SHIP_API_ID_START
        }
        family_ids = {ship_id: ship_id for ship_id in ships_by_id}

        def find_family_id(ship_id):
            if family_ids[ship_id] != ship_id:
                family_ids[ship_id] = find_family_id(family_ids[ship_id])
            return family_ids[ship_id]

        for ship in ships_by_id.values():
            after_ship_id = int(ship.get("api_aftershipid") or 0)
            if after_ship_id not in family_ids:
                continue

            source_family_id = find_family_id(ship["api_id"])
            target_family_id = find_family_id(after_ship_id)
            if source_family_id != target_family_id:
                # The smallest model ID is a stable family ID, not necessarily the
                # unremodeled (original) ship model.
                family_ids[max(source_family_id, target_family_id)] = min(
                    source_family_id, target_family_id
                )

        self.ship_family_ids = {
            ship_id: find_family_id(ship_id) for ship_id in family_ids
        }

        Log.log_debug_1("Updated ship family ID mappings:")
        for ship_id, family_id in sorted(self.ship_family_ids.items()):
            ship_name = ships_by_id[ship_id].get("api_name", "Unknown")
            family_name = ships_by_id[family_id].get("api_name", "Unknown")
            Log.log_debug_1(
                f"Ship {ship_name} (model ID: {ship_id}) -> "
                f"Family {family_name} (model ID: {family_id})"
            )

    def get_ship_family_id(self, api_id):
        return self.ship_family_ids.get(api_id, api_id)

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

    def is_same_ship(self, ship1: Ship, ship2: Ship):
        if ship1 is None or ship2 is None:
            return False
        return ship1.production_id == ship2.production_id


ships = ShipsCore()
