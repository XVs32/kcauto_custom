import config.config_core as cfg
from fleet.fleet import Fleet
from fleet.noro6 import Noro6 
import ships.ships_core as shp
from kca_enums.fleet_modes import FleetModeEnum, CombinedFleetModeEnum
from kca_enums.fleet import FleetEnum
from kca_enums.ship_types import ShipTypeEnum
from util.kc_time import KCTime
from util.logger import Log
from util.json_data import JsonData
import ships.equipment_core as equ 
import expedition.expedition_core as exp
from kca_enums.expeditions import ExpeditionEnum

import os
import copy
class FleetCore(object):
    
    EMPTY = None
     
    ACTIVE_FLEET_KEY = "active_fleet"
    EXP_POOL_KEY = "exp_pool"
    PVP_FLEET_KEY = "pvp_fleet"
    
    ASSIGN_SHIP_FAILED = -1
    ASSIGN_DRUM_FAILED = -2
    ASSIGN_LC_FAILED = -3
    
    fleets = {}
    
    
    is_custom_fleet_loaded = False

    def __init__(self):
        
        Log.log_debug("FleetCore init.")
        
        self.fleets[self.ACTIVE_FLEET_KEY] = {}
        self.fleets[self.ACTIVE_FLEET_KEY][1] = Fleet(1, FleetEnum.COMBAT)
        self.fleets[self.ACTIVE_FLEET_KEY][2] = Fleet(2, FleetEnum.EXPEDITION, False)
        self.fleets[self.ACTIVE_FLEET_KEY][3] = Fleet(3, FleetEnum.EXPEDITION, False)
        self.fleets[self.ACTIVE_FLEET_KEY][4] = Fleet(4, FleetEnum.EXPEDITION, False)
        self.fleets[self.EXP_POOL_KEY] = self.EMPTY
        self.fleets[self.PVP_FLEET_KEY] = self.EMPTY

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
                
            fleet.ship_data = []
            for ship_id in fleet_data['api_ship']:
                if ship_id != -1:
                    fleet.ship_data.append(
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
    def expedition_fleets(self):
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
            combat_ships += f.ship_data
        return combat_ships

    @property
    def active_ships(self):
        active_ships = []
        for fleet_id in self.fleets[self.ACTIVE_FLEET_KEY]:
            if self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].enabled:
                active_ships += self.fleets[self.ACTIVE_FLEET_KEY][fleet_id].ship_data
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
        else:
            Log.log_debug("Custom fleets setting is already loaded")
            return
        
        #merge custom fleets data into fleet core
        self.fleets = {**self.fleets, **self._noro6_to_kcauto()}
        
        equ.equipment.custom_equipment = equ.equipment.noro6_to_kcauto()
        
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
            if key == self.ACTIVE_FLEET_KEY or key == self.EXP_POOL_KEY or key == self.PVP_FLEET_KEY:
                continue
            
            for fleet_id in self.fleets[key]:
                for ship in self.fleets[key][fleet_id].ship_data:
                    if ship.production_id in exp_pool:
                        exp_pool.pop(ship.production_id)
                        
        self.fleets[self.EXP_POOL_KEY] = {}
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
            
    def _noro6_to_kcauto(self):
        """
            method to convert noro6 preset to kcauto preset
            output: (kcauto preset) 
        """
        
        ret = {}
        noro6 = Noro6()
 
        for preset in noro6.presets:
            noro6.get_map(preset["name"])
            ret[preset["name"]] = {}
            for fleet_id in range(1, noro6.get_fleet_count() + 1 ):
                noro6.get_fleet(fleet_id)
                ret[preset["name"]][fleet_id] = Fleet(fleet_id, noro6.get_preset_type(), False)
                
                ret[preset["name"]][fleet_id].ship_data = []
                for i in range(1, noro6.get_ship_count() + 1 ):
                    
                    ship = shp.ships.get_ship_from_noro6_ship(noro6.get_ship(i))
                    if ship == None:
                        Log.log_error(f'Something goes wrong when setting up Noro6 {preset["name"]} fleet, exiting...')
                        exit()
                    
                    else:
                        ret[preset["name"]][fleet_id].ship_data.append(ship)
                    
        return ret 
    
    def assign_exp_ship(self):
        
        noro6_available = True

        exp_ship_pool = copy.deepcopy(self.fleets[self.EXP_POOL_KEY]) 

        exp.expedition.exp_for_fleet = [None, None, None, None, None]
        fleet_id = 1
        fleet_id = self._get_next_exp_fleet_id(fleet_id)
        
        for exp_rank in exp.expedition.exp_rank:
            
            exp_static_data = exp.expedition.get_expedition_static_data(exp_rank["id"])
            
            
            if  exp_static_data != None :

                Log.log_error(f'exp id: {exp_static_data["id"]}')
                
                exp_ship_pool_bak = copy.deepcopy(exp_ship_pool)
                exp_equipment_pool_bak = copy.deepcopy(equ.equipment.equipment_exp)
                
                exp_ship_requirement = self._get_exp_ship_requirement_from_composition(exp_static_data["reqComposition"])
                
                fleet_ship_id_list, exp_ship_pool, exp_equipment_id_list = self._assign_ship( \
                    exp_ship_requirement, \
                    exp_ship_pool,
                    exp_static_data["reqDrum"],
                    exp_static_data["reqDrumCarriers"],
                    4)

                if fleet_ship_id_list == self.ASSIGN_SHIP_FAILED :
                    #failed to assign ships for this exp, restore the ship pool
                    Log.log_debug(f"ship_pool and equipment_pool restore")
                    exp_ship_pool = exp_ship_pool_bak 
                    equ.equipment.equipment_exp = exp_equipment_pool_bak
                elif fleet_ship_id_list == self.ASSIGN_DRUM_FAILED or fleet_ship_id_list == self.ASSIGN_LC_FAILED:
                    #failed to assign equipment for this exp, restore the ship pool
                    Log.log_debug(f"ship_pool and equipment_pool restore")
                    exp_ship_pool = exp_ship_pool_bak 
                    equ.equipment.equipment_exp = exp_equipment_pool_bak
                else:

                    #Save the fleetShipId
                    MORK_FLEET_ID = -1
                    self.fleets[exp_rank["id"]] = Fleet(MORK_FLEET_ID, FleetEnum.EXPEDITION, False)
                    self.fleets[exp_rank["id"]].ship_data = fleet_ship_id_list
    
                    equ.equipment.custom_equipment[exp_rank["id"]] = exp_equipment_id_list
                    exp.expedition.exp_for_fleet[fleet_id] = exp_rank["id"]

                    fleet_id = self._get_next_exp_fleet_id(fleet_id)

            elif noro6_available == True :
                Log.log_error(f'in 1')
                expEnum = ExpeditionEnum(exp_rank["id"])
                
                if expEnum.expedition in self.fleets:
                    Log.log_error(f'in 2')
                    noro6_available = False
                    fleet_id = self._get_next_exp_fleet_id(fleet_id)
                    exp.expedition.exp_for_fleet[fleet_id] = expEnum.expedition
                
            if fleet_id > 4:
                #assign for all fleets success
                break
            
        
        Log.log_error(f'last fleet id: {fleet_id}')
        Log.log_error(f'exp_for_fleet: {exp.expedition.exp_for_fleet}')
        
        if fleet_id > 4:
            #assign for all fleets successed
            Log.log_success(f"auto mode asigned ship for exp{exp.expedition.exp_for_fleet[2:]}")
            return True
        else:
            #some assign failed
            return False

    def _assign_ship(self, fleet_list, ship_pool, req_dc=0, req_dc_carrier=0, req_lc=4):
        """
            Method to assign the ship with the given fleet_list and ship_pool

            input: 
                fleet_list: The list of ship type (shipTypeEnum)
                ship_pool(dict): The pool of ship to use
                    ex. {"DD":[10,20,30], "CL":[41,42,43]}
            
            output:
                -1: failed to assign a valid fleet
                ship_id(dict): the ship to use for the specified exp
                    (ex: [14,15,62,2,1,73]
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
        
        equipment_list= {}
        assign_fleet = []
        for ship_enum in fleet_list:
            if ship_enum == ShipTypeEnum(TYPE_NA):
                #@todo: apply the wildcard handling
                ship_enum = ShipTypeEnum(TYPE_DD) 
                
            has_match_ship = False 
            ship = None
                        
            if req_lc > 0:
                for ship in ship_pool[ship_enum]:
                    if equ.equipment.is_available_category(ship, CATEGORY_LC):
                        
                        #@todo if the ship is kinu kai 2, she has +1 lc
                        
                        lc_count = min(req_lc, ship.slot_num)
                        req_lc -= lc_count
                         
                        temp_equipment_list = equ.equipment.fill_with_equipment(ship, NAME_ID_LC, lc_count)
                        
                        if temp_equipment_list != {}:
                            equipment_list = {**equipment_list, **temp_equipment_list}
                            has_match_ship = True
                            break
                        else:
                            Log.log_debug(f"fleet_switcher_core: assign LC failed for {fleet_list}")
                            return self.ASSIGN_LC_FAILED, ship_pool, equipment_list
            
            elif (req_dc > 0 or req_dc_carrier > 0):
                for ship in ship_pool[ship_enum]:
                    if equ.equipment.is_available_category(ship, CATEGORY_DRUM)\
                        and not equ.equipment.is_available_category(ship, CATEGORY_LC):
                            
                        req_dc_carrier = max(req_dc_carrier, 1) #make it at least one dc carrier needed, for easier math
                        
                        dc_count = min(req_dc - req_dc_carrier + 1 , ship.slot_num)
                        temp_equipment_list = equ.equipment.fill_with_equipment(ship, NAME_ID_DRUM, dc_count)
                        
                        req_dc -= dc_count
                        req_dc_carrier -= 1
                        
                        if temp_equipment_list != {}:
                            equipment_list = {**equipment_list, **temp_equipment_list}
                            has_match_ship = True
                            break
                        else:
                            Log.log_debug(f"fleet_switcher_core: assign drum failed for {fleet_list}")
                            return self.ASSIGN_DRUM_FAILED, ship_pool, equipment_list
                        
                if has_match_ship == False:
                    for ship in ship_pool[ship_enum]:
                        if equ.equipment.is_available_category(ship, CATEGORY_DRUM):
                            dc_count = min(req_dc, ship.slot_num)
                            temp_equipment_list = equ.equipment.fill_with_equipment(ship, NAME_ID_DRUM, dc_count)
                            
                            req_dc -= dc_count
                            req_dc_carrier -= 1
                            
                            if temp_equipment_list != {}:
                                equipment_list = {**equipment_list, **temp_equipment_list}
                                has_match_ship = True
                                break
    
                            else:
                                Log.log_debug(f"fleet_switcher_core: assign drum failed for {fleet_list}")
                                return self.ASSIGN_DRUM_FAILED, ship_pool, equipment_list
           
            if has_match_ship == False:
                for ship in ship_pool[ship_enum]:
                    
                    if not equ.equipment.is_available_category(ship, CATEGORY_DRUM) \
                        and not equ.equipment.is_available_category(ship, CATEGORY_LC):
                        has_match_ship = True
                        break
                    
                if has_match_ship == False and len(ship_pool[ship_enum]) > 0:
                    for ship in ship_pool[ship_enum]:
                        if not equ.equipment.is_available_category(ship, CATEGORY_LC):
                            has_match_ship = True
                            break
                    
                if has_match_ship == False and len(ship_pool[ship_enum]) > 0:
                    ship = ship_pool[ship_enum][0]
                    has_match_ship = True
            
            if has_match_ship == False:
                #Cannot find a valid ship
                Log.log_debug(f"fleet_core: assign ship failed for {fleet_list}")
                return self.ASSIGN_SHIP_FAILED, ship_pool, equipment_list
            else:
                assign_fleet.append(ship)
                ship_pool[ship_enum].remove(ship)
                Log.log_debug(f"fleet_core: assign ship {ship} for {fleet_list}")
                
        return assign_fleet, ship_pool, equipment_list

    def _get_next_exp_fleet_id(self, fleet_id):
        while 1:
            fleet_id+=1
            if fleet_id == 2:
                cur_fleet = cfg.config.expedition.fleet_2
            elif fleet_id == 3:
                cur_fleet = cfg.config.expedition.fleet_3
            elif fleet_id == 4:
                cur_fleet = cfg.config.expedition.fleet_4
            else:
                break

            if cur_fleet != []:
                break
        return fleet_id

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
