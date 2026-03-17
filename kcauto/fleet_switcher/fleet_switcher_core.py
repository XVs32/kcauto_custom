from util.pyvisauto import Region
from sys import exit
from random import choice
from random import randrange

import api.api_core as api
import config.config_core as cfg
import combat.combat_core as com
import pvp.pvp_core as pvp
import expedition.expedition_core as exp
import fleet.fleet_core as flt
import nav.nav as nav
import ship_switcher.ship_switcher_core as ssw
import ships.ships_core as shp
import ships.equipment_core as equ 
import util.kca as kca_u
from constants import AUTO_PRESET, OTHER_FLEET_ID
from fleet.fleet import Fleet
from ships.ship import Ship
from kca_enums.fleet import FleetEnum
from kca_enums.fleet_modes import FleetModeEnum
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.ship_types import ShipTypeEnum
from ships.equipment import Equipment 
from util.logger import Log

class FleetSwitcherCore(object):
    max_presets = 0
    next_combat_preset = None
    
    presets = {}
    custom_presets = {}
    exp_fleet_ship_id = {}
    exp_ship_pool = {}
    exp_fleet_ship_type = {}

    def __init__(self):
        self._set_next_combat_preset()

    def update_fleetpreset_data(self, data):
        # print("update_fleetpreset_data")
        self.presets = {}
        self.max_presets = data['api_max_num']
        for preset_id in data['api_deck']:
            self.presets[int(preset_id)] = [
                ship_id for ship_id in data['api_deck'][preset_id]['api_ship']
                if ship_id > -1]

    def _set_next_combat_preset(self):
        if len(cfg.config.combat.fleet_presets) > 0:
            self.next_combat_preset = choice(cfg.config.combat.fleet_presets)

    def _get_next_preset_id(self, context):
        preset_id = None
        if context == 'combat':
            preset_id = self.next_combat_preset
        elif context == 'pvp':
            preset_id = cfg.config.pvp.fleet_preset
        elif context == 'factory_develop' or context == 'factory_build':
            preset_id = AUTO_PRESET
        elif context == "expedition":
            preset_id = AUTO_PRESET
        return preset_id

    def goto(self):
        ssw.ship_switcher.goto()

    def switch_fleet(self, context):
        self.goto()
        preset_id = self._get_next_preset_id(context)

        if preset_id == AUTO_PRESET:
            
            if context == "combat":
                Log.log_msg(f"Switching to Fleet Preset for {cfg.config.combat.sortie_map.display_name}.")

                fleet_list = self._get_fleet_preset(cfg.config.combat.sortie_map.value)
                
                #Avoiding load process of fleet 2, 3 messing up fleet 1
                #Combat is a property, sort does not saved inside it
                rev_fleet_id = flt.fleets.combat_fleets_id.copy()
                rev_fleet_id.sort(reverse=True)
                for combat_fleet_id in rev_fleet_id:
                    
                    if combat_fleet_id == 3: 
                        fleet_list[3] = fleet_list[1]
                    
                    if not self.switch_to_costom_fleet_with_equipment(combat_fleet_id, fleet_list[combat_fleet_id]):
                        return False
                    
                nav.navigate.to('refresh_home')
                
                if cfg.config.combat.fleet_mode != flt.fleets.combined_flag:
                    
                    nav.navigate.to('fleetcomp')
                    if flt.fleets.combined_flag == FleetModeEnum.CTF or \
                        flt.fleets.combined_flag == FleetModeEnum.STF or \
                        flt.fleets.combined_flag == FleetModeEnum.TCF:
                        kca_u.kca.click_existing("upper_left", f'fleet|combine_cancel.png')
                    
                    if  cfg.config.combat.fleet_mode == FleetModeEnum.CTF or \
                        cfg.config.combat.fleet_mode == FleetModeEnum.STF or \
                        cfg.config.combat.fleet_mode == FleetModeEnum.TCF:
                        Log.log_msg(f"Switching to {cfg.config.combat.fleet_mode.display_name} mode.")
                        
                        #merge fleet #2 to fleet #1
                        flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][2].select()
                        start_region = kca_u.kca.find(
                            'top_submenu', f'fleet|fleet_2_active.png')
                        end_region = kca_u.kca.find(
                            'top_submenu', f'fleet|fleet_1.png')
                        kca_u.kca.drag(start_region, end_region)
                        
                        if cfg.config.combat.fleet_mode == FleetModeEnum.CTF:
                            kca_u.kca.click_existing("center", f'fleet|ctf.png') 
                        elif cfg.config.combat.fleet_mode == FleetModeEnum.STF:
                            kca_u.kca.click_existing("center", f'fleet|stf.png') 
                        elif cfg.config.combat.fleet_mode == FleetModeEnum.TCF:
                            kca_u.kca.click_existing("center", f'fleet|tcf.png')
                            
                        kca_u.kca.click_existing("lower", f'fleet|combine_fleet.png')
                        

                """Check if next combat possible, since new ship is switched in"""
                """Refresh home to update ship list"""
                com.combat.set_next_sortie_time(override=True)
                
            elif context == "pvp":
                Log.log_msg(f"Switching to PvP Preset.")

                fleet_list = self._get_fleet_preset(pvp.pvp.next_pvp_quest.name + "-pvp")
                        
                if not self.switch_to_costom_fleet_with_equipment(1, fleet_list[1]):
                    return False

            elif context == "expedition":
                Log.log_msg(f"Switching to Exp Preset.")

                fleet_id = flt.fleets.get_next_exp_fleet_id()
                while fleet_id != None and exp.expedition.exp_for_fleet[fleet_id] != None:
                    
                    DEFAULT_FLEET_ID = 1
                    temp = self._get_fleet_preset(exp.expedition.exp_for_fleet[fleet_id])[DEFAULT_FLEET_ID]
                    
                    if not self.switch_to_costom_fleet_with_equipment(fleet_id, temp):
                        return False
                    fleet_id = flt.fleets.get_next_exp_fleet_id(fleet_id)

            elif context == 'factory_develop':
                Log.log_msg(f"Switching to {cfg.config.factory.develop_secretary} for develop.")

                ssw.ship_switcher.current_page = 1
                ssw.ship_switcher.switch_slot_by_id(1,cfg.config.factory.develop_secretary)
            elif context == 'factory_build':
                Log.log_msg(f"Switching to {cfg.config.factory.build_secretary} for construction.")

                ssw.ship_switcher.current_page = 1
                ssw.ship_switcher.switch_slot_by_id(1,cfg.config.factory.build_secretary)
        elif preset_id == None:
            Log.log_debug(f"Fleet switch disabled")
        else:
            Log.log_msg(f"Switching to Fleet Preset {preset_id}.")
            if preset_id not in self.presets:
                Log.log_error(
                    f"Fleet Preset {preset_id} is not specified in-game. Please "
                    f"check your config.")
                exit(1)

            """open preset menu"""
            kca_u.kca.click_existing(
                'lower_left', 'fleetswitcher|fleetswitch_submenu.png')
            kca_u.kca.wait(
                'lower_left', 'fleetswitcher|fleetswitch_submenu_exit.png')

            list_idx = (preset_id if preset_id < 5 else 5) - 1
            idx_offset = preset_id - 5
            if idx_offset > 0:
                self._scroll_preset_list(idx_offset)

            kca_u.kca.r['top'].hover()
            preset_idx_region = Region(
                kca_u.kca.game_x + 410,
                kca_u.kca.game_y + 275 + (list_idx * 76),
                70, 45)
            kca_u.kca.click_existing(
                preset_idx_region, 'fleetswitcher|fleetswitch_button.png')
            if kca_u.kca.exists(
                    'left', 'fleetswitcher|fleetswitch_fail_check.png'):
                Log.log_error(
                    f"Could not switch in fleet preset {preset_id}. Please check "
                    f"your config and fleet presets.")
                exit(1)
            Log.log_msg(f"Fleet Preset {preset_id} loaded.")

            if context == 'combat':
                self._set_next_combat_preset()
        return True

    def switch_to_costom_fleet(self, fleet_id, costom_fleet : Fleet):
        """
            method to switch the ship in {fleet_id} to ships defined in {ship_list}

            fleet_id(int): fleet to switch, index starts from 1
            ship_list(fleetcore_obj): ships to use
        """
        
        EMPTY = -1
        retry = 0

        while True:
            
            flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].select()
            
            empty_slot_count = 0

            size = max(flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].size, costom_fleet.size)
            
            STRIKE_FLEET_SIZE = 7
            NORMAL_FLEET_SIZE = 6
            if size > STRIKE_FLEET_SIZE:
                Log.log_warn(f"kcauto tries to switch to fleet with size {size}, this may cause unexpected behavior.")
            
            if fleet_id == 3:
                size = min(STRIKE_FLEET_SIZE, size)
            else:
                size = min(NORMAL_FLEET_SIZE, size)

            any_vaild_switch = False
            retry = False
            for i in range(1,size + 1):
                if i > costom_fleet.size:
                    id = EMPTY #remove this slot
                else:
                    id = costom_fleet.ship_ids[i-1]

                if i <= len(flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids) and \
                    id == flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids[i-1]:
                    Log.log_debug("Ship loaded already for costom fleet: ")
                    continue
                
                if not ssw.ship_switcher.switch_slot_by_id(i-empty_slot_count,id):
                    #fleet data update
                    if any_vaild_switch == True:
                        Log.log_msg(f"retrying...")
                        nav.navigate.to('home')
                        self.goto()
                        retry = True 
                        break
                    else:
                        return False
                    
                else:
                    any_vaild_switch = True
                    
                if id == EMPTY:
                    empty_slot_count += 1

            if retry == True:
                continue
            else:
                break
        
        Log.log_success("load fleet done")
        return True
        
        
    def switch_to_costom_fleet_with_equipment(self, fleet_id, costom_fleet : Fleet):
        """
            method to switch the ship in {fleet_id} to ships defined in {ship_list}

            fleet_id(int): fleet to switch, index starts from 1
            custom_fleet(Fleet): Fleet obj contain ships to use
        """
        
        self._unload_fleet_required_equipment(costom_fleet)
        
        Log.log_success("unload_equipment done")
        
        nav.navigate.to('home')
        
        self.goto()
        
        self.switch_to_costom_fleet(fleet_id, costom_fleet) 
            
        self._load_equipment(fleet_id, costom_fleet)    
        Log.log_success("load equipment done")
        
        return True
    
    def _scroll_preset_list(self, target_clicks):
        Log.log_debug(f"Scrolling to target preset ({target_clicks} clicks).")
        clicks = 0
        while clicks < target_clicks:
            kca_u.kca.click_existing('lower_left', 'global|scroll_next.png')
            clicks += 1
    
    def _get_fleet_preset(self, key):
        """
            method to get the preset for combat or expedition
            input: 
                key(string): the name of combat map(ex. Bm2-1-1)
        """
        if key in flt.fleets.fleets:
            return flt.fleets.fleets[key]
        else:
            if key[0]=="B" or key[0]=="C":
                
                quest_end = key.find("-")
                
                Log.log_warn(f"Preset {str(key)} not found, use default {key[0] + key[quest_end:]}")
                key = key[0] + key[quest_end:]
            else:
                Log.log_error("Unexpected preset id:" + str(key))
            return flt.fleets.fleets[key]
              
    @property
    def _idel_ships_sorted_by_equipment(self):
        temp_list = sorted(flt.fleets.ships_not_in_fleets, key=lambda item: (item.sort_id, item.production_id ))
        temp_list = sorted(
            temp_list, key=lambda s: s.level, reverse=True)
        
        temp_list.reverse()
        
        return temp_list
        
    def _unload_fleet_required_equipment(self, target_fleet : Fleet):
        """
            method to unload the equipments used by this fleet
        """
        
        any_unload = False

        nav.navigate.to('refresh_home')
            
        unload_ships : list[Ship] = []
        needed_load = False
        for production_id in shp.ships.ship_pool:
            
            ship = shp.ships.ship_pool[production_id]
            if ship.production_id in target_fleet.ship_ids:
                
                target_ship = target_fleet.get_ship_by_production_id(ship.production_id)
                
                if ship.equipment_ids != target_ship.equipment_ids\
                or (ship.slot_ex!=None \
                    and (target_ship.slot_ex == None \
                    or ship.slot_ex.production_id != target_ship.slot_ex.production_id)):
                    needed_load = True
                    
                    if ship.slot_ex != None and target_ship.slot_ex == None:
                        Log.log_warn(f"Ship {ship.name} has a reinforce slot, but Noro6 config says she doesn't, you might want to update your config.")
                    
                    if ship.has_equipment() == True:
                        unload_ships.append(ship)
                        any_unload = True
            else: #target_config does not care this ship, but we still have to strip it if it holds any equipment we care
                
                if set(ship.equipment_ids) & set(target_fleet.equipment_ids)\
                or (ship.slot_ex!=None and ship.slot_ex.production_id in target_fleet.equipment_ids):
                    unload_ships.append(ship)
                    any_unload = True

        if any_unload == False and needed_load == True: 
            #let a random idle ship load and unload a whatever equipment
            unload_ships = [flt.fleets.fleets[flt.fleets.IDLE_FLEET_KEY][randrange(len(flt.fleets.fleets[flt.fleets.IDLE_FLEET_KEY]))]]
            while unload_ships[0].ship_type == ShipTypeEnum.AR:
                unload_ships = [flt.fleets.fleets[flt.fleets.IDLE_FLEET_KEY][randrange(len(flt.fleets.fleets[flt.fleets.IDLE_FLEET_KEY]))]]
                
            Log.log_msg(f'No equipment to unload, use {unload_ships[0].name} to update equipment list')
        
        elif any_unload == False and needed_load == False:
            Log.log_msg(f'No equipment to unload or load')
            return False
        
        equ.equipment.goto()
        
        idle_ship_list = self._idel_ships_sorted_by_equipment
        for ship in unload_ships:
            Log.log_msg(f'Need to unload equipment for {ship.api_id}/{ship.name}')
            
            self.unload_ship(ship, idle_ship_list=idle_ship_list, load_random=(any_unload == False and needed_load == True))
                   
        return any_unload
      
    def unload_ship(self, ship: Ship, idle_ship_list : list[Ship] = None, load_random = False):
        """
            unload a ship in the specified fleet, assume nav in equipment page already
            input: 
                fleet_id: int, starts from 1
                ship_id: int, ship production id
        """
        
        ships_to_check = idle_ship_list
        
        if ships_to_check == None:
            ships_to_check = self._idel_ships_sorted_by_equipment
          
        target_fleet = OTHER_FLEET_ID
        
        for fleet_id in flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY]:
            if ship.production_id in flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids:
                target_fleet = fleet_id
                break
            
        equ.equipment.goto_fleet(target_fleet)
        
        if target_fleet == OTHER_FLEET_ID:
            
            Log.log_msg(f'Ship {ship.name} is not in any fleet, unload from idle fleet')
            for k, idle_ship in enumerate(ships_to_check):
                if ship.production_id == idle_ship.production_id:
                    idx = k
                    break
            ssw.ship_switcher.select_replacement_row(row_idx=idx, ship=ship, mode= ssw.ship_switcher.EQUIPMENT_SHIP_MODE)
             
        else:
            Log.log_debug(f'Ship {ship.name} is in fleet {fleet_id}, unload from there')
            ship_position = flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids.index(ship.production_id)
            
            click_ship_in_equipment_page(ship_position)
      
        if load_random == True:
            #unload a ship to update equipment list
            kca_u.kca.click('1_slot_equipment') 
            
            ssw.ship_switcher.select_replacement_row(row_idx=randrange(10), mode= ssw.ship_switcher.EQUIPMENT_MODE)

            kca_u.kca.click_existing(
                'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')
            kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
            api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, process_all=True, timeout=30)
        
        if ship.slot_num == 1:
            Log.log_debug(f"1 slot ship")
            kca_u.kca.click('1_slot_unload_equipment')
        elif ship.slot_num == 2:
            Log.log_debug(f"2 slot ship")
            kca_u.kca.click('2_slot_unload_equipment') 
        elif ship.slot_num == 3:
            Log.log_debug(f"3 slot ship")
            kca_u.kca.click('3_slot_unload_equipment') 
        elif ship.slot_num == 4:
            Log.log_debug(f"4 slot ship")
            kca_u.kca.click('4_slot_unload_equipment') 
        elif ship.slot_num == 5:
            Log.log_debug(f"5 slot ship")
            kca_u.kca.click('5_slot_unload_equipment') 
        else:
            Log.log_warn(f"Unexpected slot number {ship.slot_num}, exiting...")
            exit(1)
            
        kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
        
        if ship.slot_ex != None and \
            ship.slot_ex != Equipment():
            Log.log_debug(f"reinforce slot ship")
            kca_u.kca.click('reinforce_slot_unload_equipment')

        kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
        
        api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, process_all=True)
        if api_result == {}:
            Log.log_error(f"Something goes wrong, skipping this round...")
            exit(1)
            
            retry = 10
            while not kca_u.kca.exists('left', 'nav|side_menu_home.png'):
                kca_u.kca.click_existing('bottom_right', 'shipswitcher|equipment_cancel_reinforce.png', cached=True)
                
                if retry > 0:
                    retry -=1
                    kca_u.sleep(1)
                else:
                    Log.log_error(f"kcauto can not figure out where it is, exiting...")
                    exit()
            #skiping unload for this ship  <= usually it is already unloaded, but api didn't update due to network delay
            
        return True
   
    def _load_equipment(self, fleet_id, fleet : Fleet):

        nav.navigate.to('home')

        load_ship_id = fleet.ship_ids
        
        if flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids != \
            fleet.ship_ids:
            Log.log_error(f"fleet {fleet_id} ship ids does not match, looks like ship load is failed, exiting...")
            exit(1)
        elif flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].under_repair == True:
            Log.log_error(f"fleet {fleet_id} is under repair, equipment load process halt")
            return 
            
        needed_load = False
        for i in range(fleet.size):
            if fleet.ships[i].equipment_ids != flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ships[i].equipment_ids:
                needed_load = True
                break
            
        if needed_load == False:
            Log.log_msg(f"equipment for fleet {fleet_id} is already loaded")
            return False    
        else:
            equ.equipment.goto()
            equ.equipment.goto_fleet(fleet_id)
            
        
        for i in range(fleet.size):
            
            if fleet.ships[i].equipment_ids == flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ships[i].equipment_ids:
                Log.log_debug(f"equipment for ship {load_ship_id[i]} is already loaded")
                continue
            
            click_ship_in_equipment_page(i)

            first_load = True
            ssw.ship_switcher.current_page = 1
            
            available_equipment_list = fleet.ships[i].available_equipments
            
            for k, equipment in enumerate(available_equipment_list):
                if k %10 == 0:  
                    Log.log_debug(f'Page {k // 10 + 1}')
                Log.log_debug(f'{k}: {equipment.name} {equipment.stars} (Production id: {equipment.production_id}, Model id: {equipment.model_id}), category id: {equipment.category}')
            
            for slot in range(fleet.ships[i].equipment_count):

                kca_u.kca.click(str(slot+1) + '_slot_equipment') 
                
                if first_load == True:
                    kca_u.kca.click_existing('upper_right', 'shipswitcher|equipment_sort_arrow.png')
                    kca_u.kca.click('equipment_sort_all')
                    first_load = False
                
                    kca_u.kca.wait('upper_right', 'shipswitcher|equipment_sort_all.png')
                
                row_id = next((j for j, equipment in enumerate(equ.equipment.equipment_pool[equ.equipment.FREE]) \
                    if equipment.production_id == fleet.ships[i].equipment_ids[slot]), -1)
                
                if row_id == -1:
                    Log.log_error(f"Cannot find equipment {fleet.ships[i].equipments[slot].name} \
                        with production id:{fleet.ships[i].equipments[slot].production_id}, did you scrapped it?")
                    exit(1)
                    
                Log.log_msg(f'Selecting {fleet.ships[i].equipments[slot].name} {fleet.ships[i].equipments[slot].stars} ★')
                ssw.ship_switcher.select_replacement_row(row_idx=row_id, mode= ssw.ship_switcher.EQUIPMENT_MODE)
                kca_u.kca.click_existing(
                    'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')
                kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, process_all=True, timeout=30)
                
            if fleet.ships[i].slot_ex != None and \
               fleet.ships[i].slot_ex.model_id != Equipment().model_id: 
                    
                kca_u.kca.click('reinforce_slot_equipment') 
                
                reinforce_equipment_list = fleet.ships[i].available_reinforcement_equipments
                
                Log.log_debug(f'Reinforcement equipment list:')
                for k, equipment in enumerate(reinforce_equipment_list):
                    if k %10 == 0:  
                        Log.log_debug(f'Page {k // 10 + 1}')
                    Log.log_debug(f'{k}: {equipment.name} {equipment.stars} (Production id: {equipment.production_id}, Model id: {equipment.model_id}), category id: {equipment.category}')

                row_id = next((j for j, equipment in enumerate(reinforce_equipment_list) \
                    if equipment.production_id == fleet.ships[i].slot_ex.production_id), -1)
                
                if row_id == -1:
                    Log.log_error(f"Cannot find equipment {fleet.ships[i].slot_ex.name} \
                        with production id:{fleet.ships[i].slot_ex.production_id}, did you scrapped it?")
                    
                    exit(1)
                    
                Log.log_msg(f'Selecting {fleet.ships[i].slot_ex.name} {fleet.ships[i].slot_ex.stars} ★')
                ssw.ship_switcher.select_replacement_row(row_idx=row_id, ship=fleet.ships[i], mode= ssw.ship_switcher.REINFORCEMENT_MODE)

                kca_u.kca.click_existing(
                    'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')
                kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, process_all=True, timeout=30)

        return True
    
def click_ship_in_equipment_page(ship_position):
    """
        method to click a ship in equipment page
        input: 
            ship_position(int): position of the ship in the fleet, starts from 0
    """
    
    Log.log_debug(f"Selecting the #{ship_position+1} ship")
    
    if ship_position+1 == 7:
        next_region = Region(
            kca_u.kca.game_x + 262,
            kca_u.kca.game_y + 676,
            32, 25)
        kca_u.kca.click(next_region)
        kca_u.kca.click('ship_'+ str(6)) 
    else:
        kca_u.kca.click('ship_'+ str(ship_position + 1))

        
fleet_switcher = FleetSwitcherCore()
