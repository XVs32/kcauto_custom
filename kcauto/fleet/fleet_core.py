import config.config_core as cfg
from fleet.fleet import Fleet
from fleet.noro6 import Noro6 
import ships.ships_core as shp
from ships.ship import Ship
from kca_enums.fleet_modes import FleetModeEnum, CombinedFleetModeEnum
from kca_enums.fleet import FleetEnum
from kca_enums.ship_types import ShipTypeEnum
from util.kc_time import KCTime
from util.logger import Log
from util.json_data import JsonData
import ships.equipment_core as equ 
from ships.equipment import Equipment as Equipment
import expedition.expedition_core as exp
from kca_enums.expeditions import ExpeditionEnum
from constants import AUTO_PRESET

import os
import copy
class FleetCore(object):
    
    EMPTY = None
     
    ACTIVE_FLEET_KEY = "active_fleet"
    EXP_POOL_KEY = "exp_pool"
    PVP_FLEET_KEY = "pvp_fleet"
    IDLE_FLEET_KEY = "idle_fleet"
    
    ASSIGN_SHIP_FAILED = -1
    ASSIGN_DRUM_FAILED = -2
    ASSIGN_LC_FAILED = -3
    
    FleetDict = dict[int, Fleet]
    fleets :dict[str | int, FleetDict | Fleet] = {}
    
    combined_flag = None
    
    is_custom_fleet_loaded = False

    def __init__(self):
        
        Log.log_debug("FleetCore init.")
        
        self.fleets[self.ACTIVE_FLEET_KEY] = {}
        self.fleets[self.ACTIVE_FLEET_KEY][1] = Fleet(1, FleetEnum.COMBAT)
        self.fleets[self.ACTIVE_FLEET_KEY][2] = Fleet(2, FleetEnum.EXPEDITION, False)
        self.fleets[self.ACTIVE_FLEET_KEY][3] = Fleet(3, FleetEnum.EXPEDITION, False)
        self.fleets[self.ACTIVE_FLEET_KEY][4] = Fleet(4, FleetEnum.EXPEDITION, False)
        self.fleets[self.EXP_POOL_KEY] = self.EMPTY # the data structure is self.fleets[self.EXP_POOL_KEY][shipTypeEnum] = [ship1, ship2, ...]
        self.fleets[self.PVP_FLEET_KEY] = self.EMPTY
        self.fleets[self.IDLE_FLEET_KEY] = self.EMPTY

    def update_fleets(self, data):
        
        fleets_in_data = []
        for fleet_data in data:
            fleet_id = fleet_data['api_id']
            fleets_in_data.append(fleet_id)
            fleet = self.fleets[self.ACTIVE_FLEET_KEY][fleet_id]
            if not fleet.enabled:
                fleet.enabled = True
            if fleet_id == 2:
                fleet.fleet_type = (
                    FleetEnum.COMBAT if self.combined_fleet else FleetEnum.EXPEDITION)
            if fleet_id == 3:
                fleet.fleet_type = (
                    FleetEnum.COMBAT if self.strike_force_fleet else FleetEnum.EXPEDITION)
            at_base = fleet_data['api_mission'][0] == 0
            if at_base != fleet.at_base:
                fleet.at_base = at_base
            return_time = KCTime.convert_epoch(fleet_data['api_mission'][2])
            if return_time != fleet.return_time:
                fleet.return_time = fleet_data['api_mission'][2]
                
            fleet.ships = []
            for ship_id in fleet_data['api_ship']:
                if ship_id != -1:
                    fleet.ships.append(
                        shp.ships.get_ship_from_production_id(ship_id)
                    )

        remove_fleets = set(fleets_in_data) - set(self.fleets[self.ACTIVE_FLEET_KEY].keys())
        for fleet_id in remove_fleets:
            self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].enabled = False
            
    @property
    def combat_fleets_id(self):
        if cfg.config.combat.enabled:
            if cfg.config.combat.fleet_mode is FleetModeEnum.STANDARD:
                return [1]
            elif cfg.config.combat.fleet_mode is FleetModeEnum.STRIKE:
                return [3]
            elif CombinedFleetModeEnum.contains_value(
                    cfg.config.combat.fleet_mode.value):
                return [1,2]

    @property
    def combat_fleets(self):
        if cfg.config.combat.enabled:
            if cfg.config.combat.fleet_mode is FleetModeEnum.STANDARD:
                return [self.fleets[self.ACTIVE_FLEET_KEY][1]]
            elif cfg.config.combat.fleet_mode is FleetModeEnum.STRIKE:
                return [self.fleets[self.ACTIVE_FLEET_KEY][3]]
            elif CombinedFleetModeEnum.contains_value(
                    cfg.config.combat.fleet_mode.value):
                return [self.fleets[self.ACTIVE_FLEET_KEY][1], self.fleets[self.ACTIVE_FLEET_KEY][2]]
        return []

    @property
    def combined_fleet(self):
        return len(self.combat_fleets) == 2

    @property
    def strike_force_fleet(self):
        return cfg.config.combat.fleet_mode is FleetModeEnum.STRIKE

    @property
    def pvp_fleet(self):
        if cfg.config.pvp.enabled:
            return self.fleets[self.ACTIVE_FLEET_KEY][1]
        return []

    @property
    def ships_in_fleets(self):
        ships = []
        for fleet_id in self.fleets[self.ACTIVE_FLEET_KEY]:
            ships.extend(self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].ship_ids)
        return ships

    @property
    def expedition_fleets(self) -> list[Fleet]:
        expedition_fleets = []
        if not cfg.config.expedition.enabled:
            return expedition_fleets

        if (
                len(cfg.config.expedition.fleet_2) > 0
                and self.fleets[self.ACTIVE_FLEET_KEY][2].enabled):
            expedition_fleets.append(self.fleets[self.ACTIVE_FLEET_KEY][2])
        if (
                not self.strike_force_fleet
                and len(cfg.config.expedition.fleet_3) > 0
                and self.fleets[self.ACTIVE_FLEET_KEY][3].enabled):
            expedition_fleets.append(self.fleets[self.ACTIVE_FLEET_KEY][3])
        if (
                len(cfg.config.expedition.fleet_4) > 0
                and self.fleets[self.ACTIVE_FLEET_KEY][4].enabled):
            expedition_fleets.append(self.fleets[self.ACTIVE_FLEET_KEY][4])
        return expedition_fleets

    @property
    def combat_ships(self):
        combat_ships = []
        for f in self.combat_fleets:
            combat_ships += f.ships
        return combat_ships

    @property
    def active_ships(self):
        active_ships = []
        for fleet_id in self.fleets[self.ACTIVE_FLEET_KEY]:
            if self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].enabled:
                active_ships += self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].ships
        return active_ships

    # fleet_id starts form 1
    def get_fleet_id_and_name(self, fleet_id):
        self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].get_fleet_id_and_name()

    def __str__(self):
        for fleet_id in self.fleets[self.ACTIVE_FLEET_KEY]:
            fleet = self.fleets[self.ACTIVE_FLEET_KEY][fleet_id]
            if fleet.enabled:
                Log.log_msg(fleet)
                
                
    def load_custom_fleets(self):
        """
            method to load the noro6 settings under config/noro6
            gets trigger on the first time when port api received
        """
        
        if self.is_custom_fleet_loaded == False:
            self.is_custom_fleet_loaded = True
        elif self.is_custom_fleet_loaded == True:
            Log.log_debug("Custom fleets setting is already loaded")
            return
        elif not cfg.config.combat.is_auto_mode and not cfg.config.expedition.is_auto_mode and not cfg.config.pvp.is_auto_mode:
            Log.log_success("Manual mode kcauto, noro6 config ignored")
            self.is_custom_fleet_loaded = True
            return
        else:
            Log.log_error("Unexpected state for noro6 config load, exiting...")
        
        #merge custom fleets data into fleet core
        self.fleets = {**self.fleets, **self._noro6_to_kcauto()}
        
        
    def load_custom_exp_pool(self):
        """
            method to get the custom exp pool data
            by exclude ships in custom fleets
            
            Assume load_custom_fleets is called
            
            output: (list of ship ids)
        """
        
        if self.fleets[self.EXP_POOL_KEY] != self.EMPTY:
            Log.log_debug("Exp pool is already loaded")
            return 
        
        self.fleets[self.EXP_POOL_KEY] = {}
        exp_pool = shp.ships.ship_pool.copy() 
        
        for key in self.fleets:
            if key == self.ACTIVE_FLEET_KEY or key == self.EXP_POOL_KEY or key == self.PVP_FLEET_KEY or key == self.IDLE_FLEET_KEY:
                continue
            
            for fleet_id in self.fleets[key]:
                for ship in self.fleets[key][fleet_id].ships:
                    if ship.production_id in exp_pool:
                        exp_pool.pop(ship.production_id)
                        
        for stype in range(0, ShipTypeEnum(0).count):
            self.fleets[self.EXP_POOL_KEY][ShipTypeEnum(stype)] = [] 
            
        for ship_id in exp_pool:
            ship = shp.ships.get_ship_from_production_id(ship_id)
            
            #if this ship is not locked, do not add to exp pool
            if ship.locked == False:
                continue
            
            self.fleets[self.EXP_POOL_KEY][ship.ship_type].append(ship) 
            
        for ship_type in self.fleets[self.EXP_POOL_KEY]:
            #sort each ship_type with ammo_max + fuel_max, if ammo_max + fuel_max are the same, sort with level
            self.fleets[self.EXP_POOL_KEY][ship_type].sort(key=lambda x: (x.ammo_max + x.fuel_max, x.level))
            
        return 
         
    def load_idle_pool(self):
        """
            method to get ships currently not used
            by exclude ships in custom fleets
            
            Assume load_custom_fleets is called
            
            output: (list of ship ids)
        """
        
        
        self.fleets[self.IDLE_FLEET_KEY] = []
        ship_pool = shp.ships.ship_pool.copy() 
        
        for key in self.fleets:
            if key != self.ACTIVE_FLEET_KEY:
                continue
            
            for fleet_id in self.fleets[key]:
                for ship in self.fleets[key][fleet_id].ships:
                    if ship.production_id in ship_pool:
                        ship_pool.pop(ship.production_id)
                        
            
        for ship_id in ship_pool:
            ship = shp.ships.get_ship_from_production_id(ship_id)
            
            #if this ship is not locked, do not add to exp pool
            if ship.locked == False:
                continue
            
            self.fleets[self.IDLE_FLEET_KEY].append(ship) 
            
        return 
            
    def _noro6_to_kcauto(self):
        """
            method to convert noro6 preset to kcauto preset
            output: (kcauto preset) 
        """
        
        equipment_pool_read_only = equ.equipment.equipment_pool[equ.equipment.ID].copy()
        
        if cfg.config.expedition.is_auto_mode == False:
            Log.log_warn("Manual expedition mode, please make sure expedition fleet doesn't occupy noro6's ship and equipment")
            
            for fleet in self.expedition_fleets:
                for ship in fleet.ships:
                    for equipment in ship.equipments:
                        equ.equipment._remove_from_pool(equipment, pool=equ.equipment.ID)
                        
        equipment_pool_bak = equ.equipment.equipment_pool[equ.equipment.ID].copy()
        
        ret = {}
        noro6 = Noro6()
        
        for preset in noro6.presets:
            
            is_first_not_exact_match = True
            
            noro6.get_map(preset["name"])
            
            fleet_type = noro6.get_preset_type()
            if fleet_type == FleetEnum.EXPEDITION:
                preset_name = exp.expedition.get_exp_enum_from_name(preset["name"].split("-")[-1])
            else:
                preset_name = preset["name"]
                
            ret[preset_name] = {}
                
            for fleet_id in range(0, noro6.get_fleet_count()):
                noro6.get_fleet(fleet_id)
                
                temp = Fleet(fleet_id + fleet_type.value, fleet_type, False)
                temp.ships = []
                    
                for i in range(1, noro6.get_ship_count() + 1 ):
                    ship = copy.deepcopy(shp.ships.get_ship_from_noro6_ship(noro6.get_ship(i))) # avoid modifying ship data in ship_pool
                    if ship == None:
                        Log.log_error(f'Something goes wrong when setting up Noro6 {preset["name"]} fleet, exiting...')
                        exit()
            
                    ship.equipments = []
                    
                    for j in range(1, noro6.get_equipment_count() + 1 ):
                        
                        this_equipment, is_exact_match = equ.equipment.get_equipment_from_noro6_equipment(noro6.get_equipment(j))
                        
                        # send warring, can't find exact same equipment
                        if this_equipment!=None and this_equipment.is_empty_equipment == False and is_exact_match == False:
                            if is_first_not_exact_match:
                                Log.log_msg(f"In Noro6 preset {preset['name']}...")
                                is_first_not_exact_match = False
                            Log.log_warn(f"Can't find exact {this_equipment.name} with {noro6.get_equipment(j)['r']}★, using the closest one with {this_equipment.stars}★")
                            
                        if this_equipment == None:
                            Log.log_error(f"Failed finding equipment for {preset['name']}, exit...")
                            exit(0)
                        
                        #check if this_equipment is eq obj
                        if not isinstance(this_equipment, Equipment):
                            Log.log_error(f"DEBUG1: hit")
                            exit(0)
                        ship.equipments.append(this_equipment)
                        
                        equ.equipment._remove_from_pool(this_equipment, pool=equ.equipment.ID)
                        
                    reinforce_equipment = noro6.get_reinforce_equipment()
                    if reinforce_equipment["i"] > 0:
                        this_equipment, is_exact_match = equ.equipment.get_equipment_from_noro6_equipment(reinforce_equipment)
                        ship.slot_ex = this_equipment

                        # send warring, can't find exact same equipment
                        if this_equipment != None and this_equipment.is_empty_equipment == False and is_exact_match == False:
                            if is_first_not_exact_match:
                                Log.log_msg(f"In Noro6 preset {preset['name']}...")
                                is_first_not_exact_match = False
                            Log.log_warn(f"Can't find exact {this_equipment.name} with {reinforce_equipment['r']}★, using the closest one with {this_equipment.stars}★")
                    
                        #remove this equipment from equipment pool
                        if  this_equipment != None and this_equipment.model_id != None:
                            equ.equipment._remove_from_pool(this_equipment, pool=equ.equipment.ID)
                    elif reinforce_equipment["i"] == 0:
                        ship.slot_ex = None
                    elif reinforce_equipment["i"] == -1:
                        ship.slot_ex = Equipment()
                    else:
                        Log.log_error(f"Unknown reinforce equipment {reinforce_equipment}, exit...")
                        exit(1)
                        
                    temp.ships.append(ship)
                
                ret[preset_name][fleet_id] = temp

            equ.equipment.equipment_pool[equ.equipment.NON_NORO6] = equ.equipment.equipment_pool[equ.equipment.ID].copy()
            #restore equipment pool for next noro6 preset
            equ.equipment.equipment_pool[equ.equipment.ID] = equipment_pool_bak.copy()                    
            
        equ.equipment.equipment_pool[equ.equipment.ID] = equipment_pool_read_only.copy()                    
               
        return ret 
 
    
    def assign_exp_ship(self):
        
        noro6_available = not exp.expedition.is_noro6_in_use()

        exp_ship_pool = copy.deepcopy(self.fleets[self.EXP_POOL_KEY])
        
        non_noro6_equipment_readonly = copy.deepcopy(equ.equipment.equipment_pool[equ.equipment.NON_NORO6])

        exp.expedition.exp_for_fleet = [None, None, None, None, None]
        fleet_id = self.get_next_exp_fleet_id()
        
        for i in range(len(exp.expedition.cur_exp)):
            if exp.expedition.cur_exp[i] != ExpeditionEnum.NULL:
                for ongoing_ship in self.fleets[self.ACTIVE_FLEET_KEY][i+1].ships:
                    for standby_ship in exp_ship_pool[ongoing_ship.ship_type][:] :
                        if standby_ship.production_id == ongoing_ship.production_id:
                            exp_ship_pool[ongoing_ship.ship_type].remove(standby_ship)
                            for equipment in ongoing_ship.equipments:
                                equ.equipment._remove_from_pool(equipment, pool=equ.equipment.NON_NORO6)
        
        for exp_in_rank in exp.expedition.exp_rank:
            
            exp_static_data = exp.expedition.get_expedition_static_data(ExpeditionEnum(exp_in_rank[exp.expedition.EXP_ENUM]))
            
            if  exp_static_data != None :

                exp_ship_pool_bak = copy.deepcopy(exp_ship_pool)
                non_noro6_equipment_pool_bak = copy.deepcopy(equ.equipment.equipment_pool[equ.equipment.NON_NORO6])
                
                exp_ship_requirement = self._get_exp_ship_requirement_from_composition(exp_static_data["reqComposition"])
                
                assigned_fleet, exp_ship_pool  = self._assign_ship( \
                    exp_ship_requirement, \
                    exp_ship_pool,
                    exp_static_data["reqDrum"],
                    exp_static_data["reqDrumCarriers"],
                    4,
                    exp_static_data["reqFlagLevel"],
                    exp_static_data["reqCombinedLevel"])

                if assigned_fleet == self.ASSIGN_SHIP_FAILED :
                    #failed to assign ships for this exp, restore the ship pool
                    Log.log_debug(f"ship_pool and equipment_pool restore")
                    exp_ship_pool = exp_ship_pool_bak 
                    equ.equipment.equipment_pool[equ.equipment.NON_NORO6] = non_noro6_equipment_pool_bak
                elif assigned_fleet == self.ASSIGN_DRUM_FAILED or assigned_fleet == self.ASSIGN_LC_FAILED:
                    #failed to assign equipment for this exp, restore the ship pool
                    Log.log_debug(f"ship_pool and equipment_pool restore")
                    exp_ship_pool = exp_ship_pool_bak 
                    equ.equipment.equipment_pool[equ.equipment.NON_NORO6] = non_noro6_equipment_pool_bak
                else:

                    #Save the fleetShipId
                    DEFAULT_FLEET_ID = 1
                    self.fleets[exp_in_rank[exp.expedition.EXP_ENUM]] = {}
                    self.fleets[exp_in_rank[exp.expedition.EXP_ENUM]][DEFAULT_FLEET_ID] = assigned_fleet
    
                    exp.expedition.exp_for_fleet[fleet_id] = exp_in_rank[exp.expedition.EXP_ENUM]

                    fleet_id = self.get_next_exp_fleet_id(fleet_id)

            elif noro6_available == True :
                expEnum = exp_in_rank[exp.expedition.EXP_ENUM]
                
                if expEnum in self.fleets:
                    Log.log_msg(f'Use Noro6 for {expEnum.expedition}')
                    noro6_available = False
                    exp.expedition.exp_for_fleet[fleet_id] = expEnum 
                    fleet_id = self.get_next_exp_fleet_id(fleet_id)
                
            if fleet_id == None:
                #assign for all fleets success
                #remaining ships in exp_ship_pool are the ships that are not used
                self.fleets[self.IDLE_FLEET_KEY] = []
                for key in exp_ship_pool:
                    for ship in exp_ship_pool[key]:
                        self.fleets[self.IDLE_FLEET_KEY].append(ship)
                break
            
        #restore the equipment pool for next assignment
        equ.equipment.equipment_pool[equ.equipment.NON_NORO6] = non_noro6_equipment_readonly
            
        if fleet_id == None:
            #assign for all fleets success
            Log.log_success(f"auto mode asigned ship for exp{[expedition.display_name if expedition != None else None for expedition in exp.expedition.exp_for_fleet[2:]]}")
            return True
        else:
            #some assign failed
            return False

    def _assign_ship(self, fleet_list : dict[ShipTypeEnum, list[Ship]], ship_pool : dict[ShipTypeEnum, list[Ship]], req_dc=0, req_dc_carrier=0, req_lc=4, req_lv_flag=0, req_lv_sum=0):
        """
            Method to assign the ship with the given fleet_list and ship_pool

            input: 
                fleet_list: The list of ship type (shipTypeEnum)
                ship_pool(dict): The pool of ship to use
                    ex. {"DD":[<list of ship() obj>], "CL":[<list of ship() obj>]}
            
            output:
                -1: failed to assign a valid fleet
                ship_id(dict): the ship to use for the specified exp
                    (ex: [])
            Note:
                This function should handle the wildcard("NA") type,
                so that the output here should not contain any "NA"
        """
        
        TYPE_NA = 0
        TYPE_DD = 2
        
        CATEGORY_DRUM = 30
        CATEGORY_LC = 24
        
        NAME_ID_DRUM = 75
        NAME_ID_LC = 68
        
        MORK_FLEET_ID = 2
        assign_fleet = Fleet(MORK_FLEET_ID, FleetEnum.EXPEDITION_PRESET, False)
        
        flag_ship = True
        pool_level_reverse = False
        
        for ship_enum in fleet_list:
            
            if assign_fleet.sum_level < req_lv_sum and pool_level_reverse == False:
                #If the current fleet level sum is less than the required level sum, assign high level ship first
                ship_pool[ship_enum].sort(key=lambda x: x.level, reverse=True)
                pool_level_reverse = True
            elif assign_fleet.sum_level >= req_lv_sum and pool_level_reverse == True:
                ship_pool[ship_enum].sort(key=lambda x: x.level)
                pool_level_reverse = False
            
            if ship_enum == ShipTypeEnum(TYPE_NA):
                #@todo: apply the wildcard handling
                ship_enum = ShipTypeEnum(TYPE_DD) 
                
            has_match_ship = False 
            ship = None
                        
            for ship in ship_pool[ship_enum]:
                if flag_ship == True and ship.level < req_lv_flag:
                    continue
                # Check if the ship could load LC first
                if req_lc > 0:
                    if equ.equipment.is_available_category(ship, CATEGORY_LC):
                        
                        #@todo if the ship is kinu kai 2, she has +1 lc
                        
                        lc_count = min(req_lc, ship.slot_num)
                         
                        temp_ship = copy.deepcopy(ship)
                        temp_ship.fill_with_equipment(NAME_ID_LC, lc_count)
                        
                        if temp_ship.equipments != []:
                            req_lc -= lc_count
                            if temp_ship.slot_ex != None:
                                temp_ship.slot_ex = Equipment()
                            assign_fleet.add_ship(temp_ship)
                            ship_pool[ship_enum].remove(ship)
                            Log.log_debug(f"fleet_core: assign ship {ship} for {fleet_list}")
                            has_match_ship = True
                            break
                        else:
                            Log.log_debug(f"fleet_switcher_core: assign LC failed for {fleet_list}")
                            return self.ASSIGN_LC_FAILED, ship_pool
            if has_match_ship == True:
                continue
                        
            for ship in ship_pool[ship_enum]:
                if flag_ship == True and ship.level < req_lv_flag:
                    continue
                # Check if the ship could load drum, if she can't load LC  
                if (req_dc > 0 or req_dc_carrier > 0):
                    if equ.equipment.is_available_category(ship, CATEGORY_DRUM):
                            
                        req_dc_carrier = max(req_dc_carrier, 1) #make it at least one dc carrier needed, for easier math
                        
                        dc_count = min(req_dc - req_dc_carrier + 1 , ship.slot_num)
                        
                        temp_ship = copy.deepcopy(ship)
                        temp_ship.fill_with_equipment(NAME_ID_DRUM, dc_count)
                        
                        if temp_ship.equipments != []:
                            req_dc -= dc_count
                            req_dc_carrier -= 1
                            if temp_ship.slot_ex != None:
                                temp_ship.slot_ex = Equipment()
                            assign_fleet.add_ship(temp_ship)
                            ship_pool[ship_enum].remove(ship)
                            Log.log_debug(f"fleet_core: assign ship {ship} for {fleet_list}")
                            has_match_ship = True
                            break
                        else:
                            Log.log_debug(f"fleet_switcher_core: assign drum failed for {fleet_list}")
                            return self.ASSIGN_DRUM_FAILED, ship_pool
            if has_match_ship == True:
                continue
            
            #sadly in this case, no ship can load LC or drum, at least now we try to load whatever ship we can find
            for ship in ship_pool[ship_enum]:
                if flag_ship == True and ship.level < req_lv_flag:
                    continue
                
                temp_ship = copy.deepcopy(ship)
                temp_ship.equipments = []
                if temp_ship.slot_ex != None:
                    temp_ship.slot_ex = Equipment()
                assign_fleet.add_ship(temp_ship)
                ship_pool[ship_enum].remove(ship)
                Log.log_debug(f"fleet_core: assign ship {ship} for {fleet_list}")
                has_match_ship = True
                break
            
            if has_match_ship == False:
                #Cannot find a valid ship
                Log.log_debug(f"fleet_core: assign ship failed for {fleet_list}")
                return self.ASSIGN_SHIP_FAILED, ship_pool
            
            flag_ship = False
            
        if assign_fleet.sum_level < req_lv_sum:
            Log.log_debug(f"fleet_core: assign ship failed for {fleet_list}, level sum is not enough")
            return self.ASSIGN_SHIP_FAILED, ship_pool
                
        return assign_fleet, ship_pool
    
    def _current_fleet_level_sum(self, fleet_list):
        sum = 0
        for ship in fleet_list:
            sum += ship.level
        return sum

    def get_next_exp_fleet_id(self, fleet_id=-1):
        
        START_UP = -1
        
        available_fleets = []
        for fleet in self.expedition_fleets:
            if exp.expedition.cur_exp[fleet.fleet_id - 1] == ExpeditionEnum.NULL:
                available_fleets.append(fleet)
            
        flag = False
        for fleet in available_fleets:
            if fleet_id == START_UP:
                return fleet.fleet_id
            
            if fleet.fleet_id == fleet_id and len(available_fleets) > 1:
                flag = True
            elif flag == True:
                return fleet.fleet_id
            
        return None

    def _get_exp_ship_requirement_from_composition(self, composition):
        """
            Convert the string composition (ex. "5DD, 1NA") to 
            fleetShipType (ex. [2, 2, 2, 2, 2, 0]
            numbers above is the "stype" of ships (0 for NA is defined by XV, not offical kancolle)
            which is the "api_name" under "api_mst_stype" in kancolle api
            
            return: list of ShipTypeEnum
        """
        fleetShipType = []

        for type in composition.split(","):
            count = int(type[:1])  # Extract the count from the substring
            item_type = type[1:]  # Extract the type from the substring

            stype = 0
            for stype in range(0, ShipTypeEnum(0).count):
                if ShipTypeEnum(stype).name == item_type:
                    break
            
            for _ in range(count):
                fleetShipType.append(ShipTypeEnum(stype))

        return fleetShipType
            
            

fleets = FleetCore()
