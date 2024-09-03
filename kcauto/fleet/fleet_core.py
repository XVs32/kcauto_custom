import config.config_core as cfg
from fleet.fleet import Fleet
from fleet.noro6 import Noro6 
import ships.ships_core as shp
from kca_enums.fleet_modes import FleetModeEnum, CombinedFleetModeEnum
from kca_enums.fleet import FleetEnum
from util.kc_time import KCTime
from util.logger import Log
from util.json_data import JsonData
import ships.equipment_core as equ 

import os
class FleetCore(object):
    
    ACTIVE_FLEET_KEY = "active_fleet"
    fleets = {}
    
    is_custom_fleet_loaded = False

    def __init__(self):
        
        Log.log_debug("FleetCore init.")
        
        self.fleets[self.ACTIVE_FLEET_KEY] = {}
        self.fleets[self.ACTIVE_FLEET_KEY][1] = Fleet(1, FleetEnum.COMBAT)
        self.fleets[self.ACTIVE_FLEET_KEY][2] = Fleet(2, FleetEnum.EXPEDITION, False)
        self.fleets[self.ACTIVE_FLEET_KEY][3] = Fleet(3, FleetEnum.EXPEDITION, False)
        self.fleets[self.ACTIVE_FLEET_KEY][4] = Fleet(4, FleetEnum.EXPEDITION, False)

    def update_fleets(self, data):
        
        print("Updating fleet data from API.") 
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
        
        print("HIT")
        print("HIT")
        print("HIT")
        
        if self.is_custom_fleet_loaded == False:
            self.is_custom_fleet_loaded = True
        else:
            Log.log_debug("Custom fleets are already loaded")
            return
        
        # read every .json file under config/noro6 folder
        NORO6_CONFIG = 'configs/noro6/noro6'
        self.fleets = self._noro6_to_kcauto(NORO6_CONFIG)
        print("PASS")
        print(self.fleets)
        input("enter")
        
        
        equ.equipment.custom_equipment = equ.equipment._noro6_to_kcauto(NORO6_CONFIG)
        
        print("equ.equipment.custom_equipmentent")
        print(equ.equipment.custom_equipment)   
        exit(0)
                
    def _noro6_to_kcauto(self, file_path):
        """
            method to convert noro6 preset to kcauto preset
            output: (kcauto preset) 
        """
        
        ret = {}
        noro6 = Noro6(file_path)
 
        for preset in noro6.presets:
            noro6.get_map(preset["name"])
            ret[preset["name"]] = {}
            for fleet_id in range(1, noro6.get_fleet_count() + 1 ):
                noro6.get_fleet(fleet_id)
                ret[preset["name"]][fleet_id] = Fleet(fleet_id, noro6.get_preset_type(), False)
                
                ret[preset["name"]][fleet_id].ship_data = []
                for i in range(1, noro6.get_ship_count() + 1 ):
                    ret[preset["name"]][fleet_id].ship_data.append(
                        shp.ships.get_ship_from_noro6_ship(noro6.get_ship(i))
                    )
                
        return ret 

fleets = FleetCore()
