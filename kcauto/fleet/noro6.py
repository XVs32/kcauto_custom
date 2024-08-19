from datetime import datetime

import config.config_core as cfg
import ships.ships_core as shp
import util.kca as kca_u
from kca_enums.damage_states import DamageStateEnum
from kca_enums.fatigue_states import FatigueStateEnum
from kca_enums.fleet import FleetEnum

from constants import VISUAL_DAMAGE, FLEET_NUMBER_ICON
from util.kc_time import KCTime
from util.logger import Log
from util.json_data import JsonData



class Noro6(object):
    
    
    
    raw = None
    
    filename = None
    fleet_key = None
    ship_key = None
    item_key = None

    def __init__(self, filepath=None):
        if filepath is not None:
            self.raw = JsonData.load_json(filepath)
            
            #get filename from filepath
            self.filename = filepath.split('/')[-1]
            
    def get_preset_type(self):
        """
        method to get the preset type of the noro6 file
        Returns:
            type: COMBAT(1), EXPEDITION(2)
        """
        if self.filename is None:
            return None
        
        if self.filename[0] == 'B':
            return FleetEnum.COMBAT
        elif self.filename[0] == 'D':
            return FleetEnum.EXPEDITION
        

    def get_fleet(self, fleet_id):
        """
        method to get a fleet's raw json by id
        Args:
            fleet_id (int): fleet id, starts from 1

        Returns:
            ret : the dict of the fleet or None if not found
        """
        if self.raw is None:
            return None
        
        key = "f" + str(fleet_id)
        
        if key in self.raw:
            self.fleet_key = key 
            return self.raw[key]

    def get_ship(self, ship_id):
        """
        method to get a ship's raw json by id
        Assume get_fleet has been called before this
        Args:
            ship_id (int): ship id, starts from 1

        Returns:
            ret : the dict of the ship or None if not found
        """
        
        if self.raw is None or self.fleet_key is None:
            return None

        key = "s" + str(ship_id)

        if key in self.raw[self.fleet_key]:
            self.ship_key = key
            return self.raw[self.fleet_key][key]
        
    def get_item(self, item_id):
        """
        method to get an item's raw json by id
        Assume get_ship has been called before this
        Args:
            item_id (int): item id, starts from 1

        Returns:
            ret : the dict of the item or None if not found
        """

        if self.raw is None or self.fleet_key is None or self.ship_key is None:
            return None

        key = "i" + str(item_id)

        if key in self.raw[self.fleet_key][self.ship_key]["items"]:
            self.item_key = key
            return self.raw[self.fleet_key][self.ship_key]["items"][key]
        
    def get_fleet_count(self):
        """
        method to get the vaild fleet count
        Returns:
            ret : the fleet count
        """

        if self.raw is None:
            return 0
        
        count = 0
        
        for i in range(1, 5): # 1 ~ 4
            key = "f" + str(i)
            if key in self.raw:
                count += 1
        
        return count

    def get_ship_count(self):
        """
        method to get the vaild ship count
        Assume get_fleet has been called before this
        Returns:
            ret : the ship count
        """

        if self.raw is None:
            return 0
        if self.raw[self.fleet_key] is None:
            return 0
        count = 0
        
        for i in range(1, 8): # 1 ~ 7
            key = "s" + str(i)
            if key in self.raw[self.fleet_key]:
                count += 1
                
        return count