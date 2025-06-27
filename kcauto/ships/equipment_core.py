from sys import exit
from ships.equipment import Equipment as eq
from util.json_data import JsonData
from util.logger import Log


class EquipmentCore(object):
    
    RAW = "raw"
    LOADED = "loaded"
    FREE = "free"
    ID = "id"
    
    NON_NORO6 = "NON_NORO6" #contain all equipments which does not exist in noro6 config
    
    equipment_pool : dict[str, list[eq]] = {}
    reinforce_general_category = {}
    reinforce_special = {}
    ship_type = []
    equipment_special = []
    
    
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
            self.ship_type = JsonData.load_json('data|temp|ship_type.json')
            self.equipment_special = JsonData.load_json('data|temp|equipment_ship_special.json')
        except FileNotFoundError as e:
            Log.log_error("Reinforce equipment data not found, please start kcauto from splash screen")
            Log.log_error(e)

        try:
            
            for raw_equipment in JsonData.load_json('data|temp|equipment_list.json'):
                self.equipment_pool[self.ID].append(eq(model_id=raw_equipment["api_slotitem_id"],production_id=raw_equipment["api_id"],
                    stars=raw_equipment["api_level"], lock=raw_equipment["api_locked"], ace=raw_equipment.get("api_alv", eq().ace)))
            self.equipment_pool[self.ID].append(eq())
        except FileNotFoundError:
            Log.log_error("Equipment data not found, please start kcauto from splash screen")
            Log.log_error(e)
            
    def _remove_from_pool(self, target_equipment : eq, pool):
        
        if target_equipment.production_id == eq().production_id:
            return
               
        for equipment in self.equipment_pool[pool]:
            if equipment.production_id == target_equipment.production_id:
                self.equipment_pool[pool].remove(equipment)
                break
            
    def _get_equipment_from_noro6_equipment(self, noro6_equipment):
        """
            method to convert noro6 equipment to kcauto equipment
            noro6_equipment (dict): noro6 equipment data
            output (int) : equipment production id
        """
        equipment_list = self._get_match_equipment(self.equipment_pool[self.ID], noro6_equipment["i"])
        
        if equipment_list == []:
            Log.log_error("can't find any match equipment")
            return None
        
        for equipment in equipment_list:
            
            #@todo handle "api_alv"/"l" (plane exp level)
            #if "api_alv" in temp_equipment[i] and "l" in noro6_equipment:
            if equipment.stars == noro6_equipment["r"]:
                return equipment
            
        #sort by the absolute value of difference between api_lv and rf
        equipment_list.sort(key=lambda x: abs(x.stars - noro6_equipment["r"]))
        # send warring, can't find exact same equipment
        if equipment_list[0].is_empty_equipment == False:
            Log.log_warn(f"Can't find exact {equipment_list[0].name} with level {noro6_equipment['r']}, using the closest one with {equipment_list[0].stars}★")

        return equipment_list[0]
        
    def get_reinforce_equipment_list(self, ship):

        equipment_list = []

        special_equipment_list = self.get_special_reinforce_equipment(ship) # sqecial equipment for this ship only
        
        keys = self.equipment_pool[self.RAW].keys()
        sorted_keys = sorted(keys, key=lambda x: (len(x), x))
        Log.log_debug(sorted_keys)

        for key in sorted_keys:
            #key is always "api_slottypeXXX"
            Log.log_debug(key)
            Log.log_debug(self.equipment_pool[self.RAW][key])
            if      int(key[12:]) in self.reinforce_general_category \
                and self.is_available_category(ship, int(key[12:])):
                equipment_list = equipment_list + self.equipment_pool[self.RAW][key]
            else:
                # see if this category has any special reinforce equipment
                for production_id in self.equipment_pool[self.RAW][key]:
                    name_id = self._get_name_id(production_id)
                    if name_id in special_equipment_list:
                        equipment_list.append(production_id)

        ret = []
        for production_id in equipment_list:
            ret.append(self.get_equipment_by_production_id(self.equipment_pool[self.ID], production_id))
            
        
        Log.log_debug(f'ship {ship.name} reinforce equipment list:')
        for i, equipment in enumerate(ret):
            if i %10 == 0:  
                Log.log_debug(f'Page {i // 10 + 1}')
            Log.log_debug(f'{i}: {equipment.name}{equipment.stars} (Production id: {equipment.production_id}, Model ID: {equipment.model_id})')
        
        return ret 

    def get_special_reinforce_equipment(self, ship):

        WILDCARD_SHIP_TYPE = "99"

        equipment_list = []

        Log.log_debug(self.reinforce_special)

        for key in self.reinforce_special:
            if \
                (self.reinforce_special[key]["api_ship_ids"] is not None \
                and \
                str(ship.api_id) in self.reinforce_special[key]["api_ship_ids"].keys())\
            or \
                (self.reinforce_special[key]["api_ctypes"] is not None \
                and \
                str(ship.ship_family) in self.reinforce_special[key]["api_ctypes"].keys())\
            or \
                (self.reinforce_special[key]["api_stypes"] is not None \
                and \
                    (str(ship.ship_type.id) in self.reinforce_special[key]["api_stypes"].keys() \
                        or\
                    WILDCARD_SHIP_TYPE in self.reinforce_special[key]["api_stypes"].keys())):
                Log.log_debug("hit")
                equipment_list.append(int(key))


        Log.log_debug("special equipment_list")
        Log.log_debug(equipment_list)

        return equipment_list

    def _get_name_id(self, production_id):
        """method to convert equipment production id to equipment name id"""
        
        ret = self.get_equipment_by_production_id(self.equipment_pool[self.ID], production_id)
        
        if ret is not None:
            return ret.model_id
        else:
            Log.log_warn(f"Cannot find production_id:{production_id} in equipment list")
            return None

    def _get_match_equipment(self, equipment_pool, model_id) -> list[eq]:
        """method to find all equipment in the equipment pool with the specified model id
            arg:
                equipment_pool (list of equipment obj): the equipment pool to search in
                model_id (int): the equipment model id to search for
        """
        
        is_any_match = False
        output_list = []

        EMPTY = 0
        if model_id != EMPTY:
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
                    Log.log_warn(f"Cannot find {equipment.name} in equipment list, looks like you don't have any")
        else:
            Log.log_debug("EMPTY equipment slot")
            output_list = [eq()]

        return output_list
    
    def get_equipment_by_production_id(self, equipment_pool, production_id):
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
            
        return eq(eq().UNKNOWN_EQUIPMENT, production_id=production_id)

    def is_available_category(self, target_ship, category_id):

        # If this ship has a special available equipment category
        target_ship_id = target_ship.api_id
        for ship_id in self.equipment_special:
            if ship_id == target_ship_id:
                if self.equipment_special[ship_id]["api_equip_type"][category_id] != None:
                    return True
                else:
                    return False

        # If this ship use general equipment category
        type_id = target_ship.ship_type.id
        for ship_id in self.ship_type:
            if ship_id["api_id"] == type_id:
                if ship_id["api_equip_type"][str(category_id)] == 1:
                    return True
                else:
                    return False

        Log.log_warn(f"Cannot find ship type id:{type_id}")
        return False
    
equipment = EquipmentCore()
