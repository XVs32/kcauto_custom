from kca_enums.fleet import FleetEnum

from constants import VISUAL_DAMAGE, FLEET_NUMBER_ICON
from util.logger import Log
import json
from util.json_data import JsonData

from util.lzstring import LZString

class Noro6(object):
    
    NORO6_CONFIG = 'configs/noro6/noro6'
    
    data = None
    
    presets = []
    map = None
    fleet = None
    ship = None
    item = None

    def __init__(self, filepath=NORO6_CONFIG):
        
        self.presets = []
        
        if filepath is not None:
            
            with open(filepath, 'r', encoding='utf-8') as file:
                compressed = file.read()

            decompressed = LZString.decompressFromUTF16(compressed)
            
            #read decompress as json
            data = json.loads(decompressed)
            self.data = data["savedata"]
            self.get_presets(self.data)
            
        self.map = None
        self.fleet = None
        self.ship = None
        self.item = None
                
    def get_presets(self, config):
        
        if config["isDirectory"] == True:
            for item in config["childItems"]:
                self.get_presets(item)
        else:
            self.presets.append(config)
            
    def get_map(self, name):
        
        """
        method to get the config by name
        Returns:
        """
        for preset in self.presets:
            if preset["name"] == name:
                self.map = preset
                self.fleet = None
                self.ship = None
                self.item = None
                return preset
            
        IndexError(f"can't find map {name} in noro6")
        
    def get_variant(self, map_name):
        """
            method to get all variant under a map
            map_name(str): map name
            Returns:
                list: list of variant name
        """
        ret = []
        for preset in self.presets:
            if preset["name"] == map_name or preset["name"][:preset["name"].rfind("-")] == map_name:
                ret.append(preset["name"])
                
        return ret
            
    def get_preset_type(self):
        """
        method to get the preset type of the noro6 file
        Returns:
            type: COMBAT(1), EXPEDITION(2)
        """
        if self.map is None:
            return None
        
        if self.map["name"][0] == 'B':
            return FleetEnum.COMBAT
        elif self.map["name"][0] == 'C':
            return FleetEnum.COMBAT
        elif self.map["name"][0] == 'D':
            return FleetEnum.EXPEDITION
        else:
            return FleetEnum.COMBAT

    def get_fleet(self, fleet_id):
        """
        method to get a fleet's raw json by id
        Args:
            fleet_id (int): fleet id, starts from 1

        Returns:
            ret : the dict of the fleet or None if not found
        """
        #handle key not found error
        
        if "manager" not in self.map:
            return None
        if "fleetInfo" not in self.map["manager"]:
            return None
        #read string in self.map["manager"] as json
        fleetInfo = json.loads(self.map["manager"])["fleetInfo"]
        
        if fleetInfo is None:
            return 0
        if len(fleetInfo["fleets"]) < fleet_id:
            return None
        
        self.ship = None
        self.item = None
        
        self.fleet = fleetInfo["fleets"][fleet_id-1]
        return self.fleet

    def get_ship(self, ship_id):
        """
        method to get a ship's raw json by id
        Assume get_fleet has been called before this
        Args:
            ship_id (int): ship id, starts from 1

        Returns:
            ret : the dict of the ship or None if not found
        """
        if self.fleet is None:
            return None

        if len(self.fleet["ships"]) < ship_id:
            return None

        self.item = None
        self.ship = self.fleet["ships"][ship_id-1]
        return self.ship
        
        
    def get_equipment(self, item_id):
        """
        method to get an item's raw json by id
        Assume get_ship has been called before this
        Args:
            item_id (int): item id, starts from 1

        Returns:
            ret : the dict of the item or None if not found
        """
        if self.ship is None:
            return None

        if len(self.ship["is"]) < item_id:
            return None

        self.item = self.ship["is"][item_id-1]
        
        if 'r' not in self.item:
            self.item['r'] = 0
        if 'l' not in self.item:
            self.item['l'] = 0
        
        return self.item
    
    def get_reinforce_equipment(self):
        """
        method to get the reinforce equipment
        Assume get_ship has been called before this
        Returns:
            ret : the dict of the reinforce equipment or None if not found
        """
        if self.ship is None:
            return None
        
        self.item = self.ship["ex"]
        
        #if reinforce slot enable but empty
        if self.ship["re"] is True and self.item['i'] == 0:
            self.item['i'] = -1
        
        if 'r' not in self.item:
            self.item['r'] = 0
        if 'l' not in self.item:
            self.item['l'] = 0
        return self.item
        
    def get_fleet_count(self):
        """
        method to get the vaild fleet count
        Returns:
            ret : the fleet count
        """
        if self.map is None:
            return 0
        if self.map["manager"] is None:
            return 0
        
        #read string in self.map["manager"] as json
        fleetInfo = json.loads(self.map["manager"])["fleetInfo"]
        
        if fleetInfo is None:
            return 0
        count = len(fleetInfo["fleets"])

        return count

    def get_ship_count(self):
        """
        method to get the vaild ship count
        Assume get_fleet has been called before this
        Returns:
            ret : the ship count
        """
        if self.fleet is None:
            return 0
        count = 0
        for ship in self.fleet["ships"]:
            if ship["i"] != 0 :
                count += 1
        
        return count
    
    def get_equipment_count(self):
        """
        method to get the vaild equipment count
        Assume get_ship has been called before this
        Returns:
            ret : the equipment count
        """

        if self.ship is None:
            return 0
        count = len(self.ship["is"])
                
        return count
    
    def print_status(self):
        Log.log_debug(f"map: {self.map['name']}")
        Log.log_debug(f"fleet: {self.fleet}") if self.fleet is not None else None
        Log.log_debug(f"ship: {self.ship}") if self.ship is not None else None
        Log.log_debug(f"item: {self.item}") if self.item is not None else None