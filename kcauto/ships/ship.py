from datetime import timedelta

from kca_enums.damage_states import DamageStateEnum
from kca_enums.fatigue_states import FatigueStateEnum
from kca_enums.ship_types import ShipTypeEnum
import ships.equipment_core as equ 
from ships.equipment import Equipment
from util.kc_time import KCTime
from util.logger import Log


class Ship(object):
    
    EMPTY_LOCAL_DATA = {
        'api_id': 0,
        'api_lv':0,
        'api_nowhp':0,
        'api_maxhp':0,
        'api_bull':0,
        'api_fuel':0,
        'api_cond':0,
        'api_locked':False,
        'api_ndock_time':0,
        'api_slot_ex':0
    }
    
    _name = None
    _name_jp = None
    api_id = None       #ship name id
    sortno = None       #Id used in ship switcher, picture book id 
    sort_id = None      #Sorting Id
    ship_type = None    #stype api
    ship_family = None  #ctype api
    slot_num = None
    production_id = None     #The production code of a ship
    level = None
    hp = None
    hp_max = None
    ammo = None
    ammo_max = None
    fuel = None
    fuel_max = None
    morale = None
    locked = None
    ndock_time_ms = None
    slot_ex : Equipment = None
    
    equipments : list[Equipment] = []

    def __init__(self, static_data, local_data : dict):
        
        self.api_id = static_data['api_id']
        self.sortno = static_data['api_sortno']
        self.sort_id = static_data['api_sort_id']
        self.name = static_data['api_name']
        self.name_jp = static_data['api_name']
        self.ship_type = ShipTypeEnum(static_data['api_stype'])
        self.ship_family = static_data['api_ctype']
        self.slot_num = static_data['api_slot_num']
        self.ammo_max = static_data['api_bull_max']
        self.fuel_max = static_data['api_fuel_max']

        self.production_id = local_data['api_id']
        self.level = local_data['api_lv']
        self.hp = local_data['api_nowhp']
        self.hp_max = local_data['api_maxhp']
        self.ammo = local_data['api_bull']
        self.fuel = local_data['api_fuel']
        self.morale = local_data['api_cond']
        self.locked = local_data['api_locked'] == 1
        self.ndock_time_ms = local_data['api_ndock_time']
        
        self.equipments = []
        for equipment_production_id in local_data.get("api_slot", []):
            if equipment_production_id > 0:
                self.equipments.append(
                    equ.equipment.get_equipment_by_production_id(equ.equipment.equipment_pool[equ.equipment.ID], equipment_production_id))
            
        if local_data['api_slot_ex'] == -1:
            self.slot_ex = Equipment()
        elif local_data['api_slot_ex'] == 0:
            self.slot_ex = None
        elif local_data['api_slot_ex'] > 0:
            self.slot_ex = equ.equipment.get_equipment_by_production_id(equ.equipment.equipment_pool[equ.equipment.ID], local_data['api_slot_ex']) 
        else:
            Log.log_error(f"Unknown slot_ex equipment: {local_data['api_slot_ex']} not found, exiting...")
            exit(1)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def name_jp(self):
        return self._name_jp
    @name_jp.setter
    def name_jp(self, value):
        self._name_jp = value


    @property
    def hp_p(self):
        return self.hp / self.hp_max

    @property
    def damage(self):
        if self.hp == -1:
            return DamageStateEnum.RETREATED
        else:
            return DamageStateEnum.get_damage_state_from_hp_percent(self.hp_p)

    @property
    def fatigue(self):
        return FatigueStateEnum.get_fatigue_state_from_morale(self.morale)

    @property
    def ringed(self):
        return self.level >= 100

    @property
    def needs_resupply(self):
        if self.fuel < self.fuel_max:
            return True
        if self.ammo < self.ammo_max:
            return True
        return False

    @needs_resupply.setter
    def needs_resupply(self, value):
        if type(value) is not bool:
            raise TypeError("need resupply value is not bool.")
        if value is True:
            self.ammo = 0
            self.fuel = 0
        else:
            self.ammo = self.ammo_max
            self.fuel = self.fuel_max

    @property
    def repair_time_delta(self):
        if type(self.ndock_time_ms) is int:
            return KCTime.seconds_to_timedelta(self.ndock_time_ms // 1000)
        return timedelta(seconds=0)

    def repair(self):
        self.hp = self.hp_max

    def __repr__(self):
        return (
            f"{self.name} (#{self.sortno}:{self.api_id}:{self.sort_id}) / "
            f"{self.ship_type.name} lvl{self.level} ({self.production_id}) / "
            f"HP:{self.hp}/{self.hp_max} ({self.hp_p:.3n}:"
            f"{self.damage.name}) / "
            f"F:{self.fuel}/{self.fuel_max} / "
            f"A:{self.ammo}/{self.ammo_max} / "
            f"M:{self.morale} ({self.fatigue.name})")
    
    def has_no_equipment(self):
        """
        Checks if the ship has no equipment equipped.
        Returns True if no equipment is equipped, False otherwise.
        """
        for equipment in self.equipments:
            if equipment.model_id > 0:
                return False
            
        if self.slot_ex != None and self.slot_ex.model_id > 0:
            return False
        
        return True
    
    
    @property
    def equipment_ids(self):
        """
        Returns a list of equipment production ids equipped on the ship.
        """
        ids = []
        for equipment in self.equipments:
            if equipment.model_id > 0:
                ids.append(equipment.production_id)
        if self.slot_ex != None and self.slot_ex.model_id > 0:
            ids.append(self.slot_ex.production_id)
        
        return ids    

    @property
    def equipment_count(self):
        """
        Returns the count equipments on board, slot_ex is not included
        """
        count = 0
        for equipment in self.equipments:
            if equipment.model_id > 0:
                count += 1
        return count
    
    
    
    def fill_with_equipment(self, model_id : int, count : int, sort_by_level : bool = False) -> dict[int, list[int]]:
        """
            method to fill a ship with one type of equipment
            
            arg:
                ship (Ship): ship instance
                equipment (int): equipment model id
                count (int): how many equipment to fill
                sort_by_level (bool): if True, use high level equipment first
            
            output a kcauto format ship equipment list
        """
        
        self.equipments = []
        
        count = min(count, self.slot_num)
        
        temp_equipment = equ.equipment._get_match_equipment(equ.equipment.equipment_pool[equ.equipment.NON_NORO6], model_id)
        count = min(count, len(temp_equipment))
        
        self.equipments = temp_equipment[:count]
        
        for i in range(count):
            equ.equipment._remove_from_pool(target_equipment=temp_equipment[i], pool=equ.equipment.NON_NORO6)
        
        return 