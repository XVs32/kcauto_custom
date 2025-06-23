from util.logger import Log
from util.json_data import JsonData

class Equipment():

    UNKNOWN_EQUIPMENT = 0
    EMPTY_EQUIPMENT = -1
    
    equipment_static_data = {}
    
    model_id = 0
    production_id = 0
    stars = 0
    lock = 0
    ace = 0 
    
    def __init__(self, model_id = -1, production_id = -1, stars = -1, lock = -1, ace = -1):
        self.update(model_id, production_id, stars, lock, ace)
        
        if Equipment.equipment_static_data == {}:
            try:
                Log.log_debug("Loading equipment static data.")
                Equipment.equipment_static_data = JsonData.load_json('data|temp|equipment_static.json')
            except FileNotFoundError as e:
                Log.log_error("Equipment data not found, please start kcauto from splash screen")
                Log.log_error(e)

    def update(self, model_id = None, production_id = None, stars = None, lock = None, ace = None):
        if model_id is not None:
            self.model_id = model_id

        if production_id is not None:
            self.production_id = production_id
        
        if stars is not None:
            self.stars = stars
        
        if lock is not None:
            self.lock = lock
            
        if ace is not None:
            self.ace = ace
    
    @property 
    def static_data(self):
        """
            method to get the static data of an equipment by its model id
            input: model_id (int): the equipment model id
            output: equipment static data (dict)
        """
        
        for equipment in Equipment.equipment_static_data:
            if equipment["api_id"] == self.model_id:
                return equipment
        
        Log.log_error(f"Cannot find model_id:{self.model_id} in equipment static data, something is wrong with the api data")
        Log.log_debug(f"equipment data:")
        Log.log_debug(f"model_id: {self.model_id}")
        Log.log_debug(f"production_id: {self.production_id}")
        Log.log_debug(f"stars: {self.stars}")
        Log.log_debug(f"lock: {self.lock}")
        Log.log_debug(f"ace: {self.ace}")
        
    @property
    def name(self):
        """
            method to get the equipment name
            output: equipment name (str)
        """
        return self.static_data['api_name']

    @property
    def is_empty_equipment(self):
        return self.model_id == self.EMPTY_EQUIPMENT

    @property
    def is_unknown_equipment(self):
        return self.model_id == self.UNKNOWN_EQUIPMENT