from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ships.ship import Ship

from ships.equipment import Equipment
from util.json_data import JsonData
from util.logger import Log
from kca_enums.ship_class import ShipClassEnum 
from kca_enums.ship_types import ShipTypeEnum
from constants import FLEET_ID_ICON

import nav.nav as nav
import util.kca as kca_u

class EquipmentCore(object):
    
    RAW = "raw"
    LOADED = "loaded"
    FREE = "free"
    ID = "id"
    
    NON_NORO6 = "NON_NORO6" #contain all equipments which does not exist in noro6 config
    
    equipment_pool : dict[str, list[Equipment]] = {}
    reinforce_general_category = {}
    reinforce_special = {}
    ship_type_static = []
    equipment_special = []
    
    current_ship_list_page = 1
    current_fleet = 1
    
    is_custom_fleet_equipment_loaded = False
    
    EQUIPMENT_NAME_KEY = "api_name"
    
    SLOT_EX_NOT_AVAILABLE = 0

    def __init__(self):
        self.equipment_pool[self.RAW] = {}
        self.equipment_pool[self.LOADED] = []
        self.equipment_pool[self.FREE] = []
        self.equipment_pool[self.ID] = []
        self.equipment_pool[self.NON_NORO6] = []

        try:
            self.reinforce_general_category = JsonData.load_json('data|temp|reinforce_general_category.json')
            self.reinforce_special = JsonData.load_json('data|temp|reinforce_special.json')
            self.ship_type_static = JsonData.load_json('data|temp|ship_type.json')
            self.equipment_special = JsonData.load_json('data|temp|equipment_ship_special.json')
        except FileNotFoundError as e:
            Log.log_error("Reinforce equipment data not found, please start kcauto from splash screen")
            Log.log_error(e)

        try:
            
            for raw_equipment in JsonData.load_json('data|temp|equipment_list.json'):
                self.equipment_pool[self.ID].append(Equipment(model_id=raw_equipment["api_slotitem_id"],production_id=raw_equipment["api_id"],
                    stars=raw_equipment["api_level"], lock=raw_equipment["api_locked"], ace=raw_equipment.get("api_alv", Equipment().ace)))
            self.equipment_pool[self.ID].append(Equipment())
        except FileNotFoundError:
            Log.log_error("Equipment data not found, please start kcauto from splash screen")
            Log.log_error(e)
            
    def goto(self):
        nav.navigate.to('equipment')
        self.current_ship_list_page = 1
        self.current_fleet = 1
        
    def goto_fleet(self, fleet_id):
        """method to navigate to the fleet in equipment page, page 'other' as treated as fleet 999

        Args:
            fleet_id (_type_): _description_
        """
        
        kca_u.kca.wait("left", f"nav|side_menu_equipment_active.png")
        while True:
            kca_u.kca.click_existing("upper_left", f"fleet|fleet_{fleet_id}.png")
            if  kca_u.kca.exists("upper_left", f"fleet|fleet_{fleet_id}_active.png", similarity=FLEET_ID_ICON):
                break
            kca_u.kca.sleep(1)
        
        if fleet_id != self.current_fleet:
            self.current_ship_list_page = 1 
            self.current_fleet = fleet_id
        
        return
            
    def _remove_from_pool(self, target_equipment : Equipment, pool):
        
        if target_equipment.production_id == Equipment().production_id:
            return
               
        for equipment in self.equipment_pool[pool]:
            if equipment.production_id == target_equipment.production_id:
                self.equipment_pool[pool].remove(equipment)
                break
            
    def get_equipment_from_noro6_equipment(self, noro6_equipment):
        """
            method to convert noro6 equipment to kcauto equipment
            noro6_equipment (dict): noro6 equipment data
            output (int) : equipment production id
            output (bool) : is exact match
        """
        
        equipment_list = self._get_match_equipment(self.equipment_pool[self.ID], noro6_equipment["i"])
        
        if equipment_list == []:
            Log.log_error("can't find any match equipment")
            return None, False
        
        for equipment in equipment_list:
            
            #@todo handle "api_alv"/"l" (plane exp level)
            #if "api_alv" in temp_equipment[i] and "l" in noro6_equipment:
            if equipment.stars == noro6_equipment["r"]:
                return equipment, True
            
        #sort by the absolute value of difference between api_lv and rf
        equipment_list.sort(key=lambda x: abs(x.stars - noro6_equipment["r"]))
            
        return equipment_list[0], False
    
        
    def get_reinforce_equipment_list(self, ship : Ship):

        ret = []

        special_equipment_list = self._get_special_reinforce_equipment(ship) # sqecial equipment for this ship only
        
        for equipment in self.equipment_pool[self.FREE]:
            if equipment.model_id in special_equipment_list:
                if equipment.stars >= special_equipment_list[equipment.model_id]:
                    ret.append(equipment)
            elif equipment.category in self.reinforce_general_category and \
                self.is_available_equipment(ship, equipment):
                    ret.append(equipment)
            else:
                Log.log_debug(f"Equipment {equipment.name} ({equipment.production_id}) is not available for ship {ship.name}, skipping")
                

        Log.log_debug(f'ship {ship.name} reinforce equipment list:')
        for i, equipment in enumerate(ret):
            if i %10 == 0:  
                Log.log_debug(f'Page {i // 10 + 1}')
            Log.log_debug(f'{i}: {equipment.name}{equipment.stars} (Production id: {equipment.production_id}, Model ID: {equipment.model_id})')
        
        
        return ret 

    def _get_special_reinforce_equipment(self, ship: Ship):
        """method to get the special reinforce equipment for the ship
        Args:
            ship (Ship): the ship to check
        Returns:
            dict: a dictionary with key as equipment production id and value as required level
        """

        WILDCARD_SHIP_TYPE = "99"

        equipment_list = {}

        Log.log_debug(self.reinforce_special)

        for key in self.reinforce_special:
            if \
                (self.reinforce_special[key]["api_ship_ids"] is not None \
                and \
                str(ship.api_id) in self.reinforce_special[key]["api_ship_ids"].keys())\
            or \
                (self.reinforce_special[key]["api_ctypes"] is not None \
                and \
                ship.ship_class in [ShipClassEnum(int(reinforce_ship_class)) for reinforce_ship_class in self.reinforce_special[key]["api_ctypes"].keys()])\
            or \
                (self.reinforce_special[key]["api_stypes"] is not None \
                and \
                set([ship.ship_type,ShipTypeEnum.WILDCARD]).intersection(set([ShipTypeEnum(int(reinforce_ship_type)) for reinforce_ship_type in self.reinforce_special[key]["api_stypes"].keys()]))):
                Log.log_debug("hit")
                equipment_list[(int(key))] = self.reinforce_special[key]["api_req_level"]
 
        Log.log_debug("special equipment_list")
        Log.log_debug(equipment_list)

        return equipment_list

    def _get_model_id(self, production_id):
        """method to convert equipment production id to equipment name id"""
        
        ret = self.get_equipment_by_production_id(self.equipment_pool[self.ID], production_id)
        
        if ret is not None:
            return ret.model_id
        else:
            Log.log_warn(f"Cannot find production_id:{production_id} in equipment list")
            return None

    def _get_match_equipment(self, equipment_pool, model_id) -> list[Equipment]:
        """method to find all equipment in the equipment pool with the specified model id
            arg:
                equipment_pool (list of equipment obj): the equipment pool to search in
                model_id (int): the equipment model id to search for
        """
        
        is_any_match = False
        output_list = []
        

        if model_id != Equipment.EMPTY_EQUIPMENT and model_id != Equipment.UNKNOWN_EQUIPMENT:
            for equipment in equipment_pool:
                if equipment.model_id == model_id:
                    output_list.append(equipment)
                    is_any_match = True

            if is_any_match != True:
                for equipment in self.equipment_pool[self.ID]:
                    if equipment.model_id == model_id:
                        Log.log_warn(f"Cannot find {equipment.name} in equipment pool, maybe it is in use")
                        is_any_match = True
                        break
                if is_any_match != True:
                    temp = Equipment(model_id=model_id)
                    Log.log_warn(f"Cannot find {temp.name} in equipment list, looks like you don't have any")
        else:
            Log.log_debug("EMPTY equipment slot")
            output_list = [Equipment()]

        return output_list
    
    def get_equipment_by_production_id(self, equipment_pool : list[Equipment], production_id) -> Equipment:
        """
        method to get the equipment by its production id

        Args:
            equipment_pool (list of equipment obj): the equipment pool to search in
            production_id (int): the equipment production id
        """
        for equipment in equipment_pool:
            if equipment.production_id == production_id:
                return equipment
        
        for equipment in self.equipment_pool[self.ID]:
            if equipment.production_id == production_id:
                Log.log_warn(f"Cannot find {equipment.name} in specified equipment pool, maybe it is in use")
                return None 
            
        return Equipment(Equipment().UNKNOWN_EQUIPMENT, production_id=production_id)

    def is_available_category(self, target_ship, category_id):
        
        NON_NONE = 0

        # If this ship has a special available equipment category
        target_ship_id = str(target_ship.api_id)
        
        if target_ship_id in self.equipment_special:
            if self.equipment_special[target_ship_id]["api_equip_type"].get(str(category_id), NON_NONE) == None:
                return True
            else:
                return False

        # If this ship use general equipment category
        type_id = target_ship.ship_type.id
        for ship_type_static_info in self.ship_type_static:
            if ship_type_static_info["api_id"] == type_id:
                if ship_type_static_info["api_equip_type"][str(category_id)] == 1:
                    return True
                else:
                    return False

        Log.log_warn(f"Cannot find ship type id:{type_id}")
        return False
 
    def is_available_equipment(self, ship: Ship, equipment: Equipment):
        
        """method to check if the equipment is available for the ship
        Args:
            ship (Ship): the ship to check
            equipment (Equipment): the equipment to check
        """
        
        if self.is_available_category(ship, equipment.category) == True:
            return True
        else:
            ship_id = str(ship.api_id)
            
            if ship_id in self.equipment_special:
                if str(equipment.category) in self.equipment_special[ship_id]["api_equip_type"] \
                and equipment.model_id in self.equipment_special[ship_id]["api_equip_type"][str(equipment.category)]:
                    return True
                else:
                    return False
        
        return False
    
equipment = EquipmentCore()
