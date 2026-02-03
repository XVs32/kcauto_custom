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
    
    _category = None
    
    def __init__(self, model_id = -1, production_id = -1, stars = -1, lock = -1, ace = -1):
        self.update(model_id, production_id, stars, lock, ace)
        
        if Equipment.equipment_static_data == {}:
            Equipment.staic_data_reload()
                
    def staic_data_reload():
        """
            method to reload the static data of equipment from json file
        """
        try:
            Log.log_debug("Reloading equipment static data.")
            temp = JsonData.load_json('data|temp|equipment_static.json')
            for item in temp:
                Equipment.equipment_static_data[item['api_id']] = item
            
        except FileNotFoundError as e:
            Equipment.equipment_static_data = None
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
        return Equipment.equipment_static_data.get(self.model_id, None)
        
        Log.log_error(f"Cannot find model_id:{self.model_id} in equipment static data, something is wrong with the api data")
        Log.log_debug(f"equipment data:")
        Log.log_debug(f"model_id: {self.model_id}")
        Log.log_debug(f"production_id: {self.production_id}")
        Log.log_debug(f"stars: {self.stars}")
        Log.log_debug(f"lock: {self.lock}")
        Log.log_debug(f"ace: {self.ace}")
        
    def category_patch(model_id, new_category):
        """
            method to patch the equipment category, since the api data is wrong for some equipment
            input: model_id (int): the equipment model id
                   new_category (ing): the new category to patch
        """
        if model_id in Equipment.equipment_static_data:
            Equipment.equipment_static_data[model_id]['api_type'][2] = new_category
            Log.log_debug(f"Patched equipment model_id:{model_id} to category:{new_category}")
        else:
            Log.log_error(f"Cannot find model_id:{model_id} in equipment static data, cannot patch category")
            
        return
        
    @property
    def name(self):
        """
            method to get the equipment name
            output: equipment name (str)
        """
        return self.static_data['api_name']
    
    @property
    def category(self):
        """
            method to get the equipment category
            output: equipment category (int)
        """
        if self._category == None:
            self._category = self.static_data['api_type'][2]
        return self._category
    
    @category.setter
    def category(self, value):
        self._category = value

    @property
    def is_empty_equipment(self):
        return self.model_id == self.EMPTY_EQUIPMENT

    @property
    def is_unknown_equipment(self):
        return self.model_id == self.UNKNOWN_EQUIPMENT