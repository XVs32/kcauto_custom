from util.pyvisauto import Region
from sys import exit
from random import choice
from random import randrange

import api.api_core as api
import config.config_core as cfg
import combat.combat_core as com
import expedition.expedition_core as exp
import fleet.fleet_core as flt
import nav.nav as nav
import ship_switcher.ship_switcher_core as ssw
import ships.ships_core as shp
import ships.equipment_core as equ 
import util.kca as kca_u
from constants import AUTO_PRESET
from fleet.fleet import Fleet
from kca_enums.fleet import FleetEnum
from kca_enums.fleet_modes import FleetModeEnum
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.ship_types import ShipTypeEnum
from ships.equipment import Equipment 
from util.logger import Log

class FleetSwitcherCore(object):
    max_presets = 0
    presets = {}
    next_combat_preset = None
    
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

                fleet_list = self._get_fleet_preset("C-pvp")
                        
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
                kca_u.kca.sleep()
                self._scroll_preset_list(idx_offset)

            kca_u.kca.r['top'].hover()
            kca_u.kca.sleep()
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
            kca_u.kca.sleep(0.1)
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
            if key[0]=="B":
                
                quest_end = key.find("-")
                
                Log.log_warn(f"Preset {str(key)} not found, use default {key[0] + key[quest_end:]}")
                key = key[0] + key[quest_end:]
            else:
                Log.log_error("Unexpected preset id:" + str(key))
            return flt.fleets.fleets[key]
              
    def _unload_fleet_required_equipment(self, target_fleet : Fleet):
        """
            method to unload the equipments used by this fleet
        """
        
        any_unload = False

        nav.navigate.to('refresh_home')
            
        unload_ships = []
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
                    
                    if ship.has_no_equipment() == False:
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
        
        start_id = 0
        while len(unload_ships) > start_id:
            
            fleet_size = min(6, len(unload_ships) - start_id)
            
            self.goto()
            
            TEMP_FLEET_ID = 1
            temp = (Fleet("unload_equipment", FleetEnum.COMBAT, False))
            temp.ships = unload_ships[start_id:start_id + fleet_size]
            
            if self.switch_to_costom_fleet(TEMP_FLEET_ID, temp):
                nav.navigate.to('refresh_home')
            else:
                Log.log_error("kcauto failed to load the selected ship, exiting...")
                break
                
            nav.navigate.to('equipment')

            self.unload_fleet_equipment(fleet_id=TEMP_FLEET_ID, needed_load=(any_unload==False and needed_load==True))

            start_id += fleet_size

        return any_unload
      
    def unload_ship(self, fleet_id = 1, ship=None):
        """
            unload a ship in the specified fleet, assume nav in equipment page already
            input: 
                fleet_id: int, starts from 1
                ship_id: int, ship production id
        """
         
        self.goto()
        
        temp_fleet = (Fleet("unload_equipment", FleetEnum.COMBAT, False))
        temp_fleet.ships = []
        temp_fleet.ships.append(ship)
        
        if not self.switch_to_costom_fleet(fleet_id, temp_fleet):
            Log.log_error("kcauto failed to load the selected ship, exiting...")
            return False
            
        nav.navigate.to('equipment')

        Log.log_debug(f"unload the {1} ship")
        kca_u.kca.click('ship_'+ str(1)) 
        
        while True:
            
            if kca_u.kca.exists('equipment_panel', 'shipswitcher|1_slot_ship.png'):
                Log.log_debug(f"1 slot ship")
                kca_u.kca.click('1_slot_unload_equipment')
            elif kca_u.kca.exists('equipment_panel', 'shipswitcher|2_slot_ship.png',cached=True):
                Log.log_debug(f"2 slot ship")
                kca_u.kca.click('2_slot_unload_equipment') 
            elif kca_u.kca.exists('equipment_panel', 'shipswitcher|3_slot_ship.png',cached=True):
                Log.log_debug(f"3 slot ship")
                kca_u.kca.click('3_slot_unload_equipment') 
            elif kca_u.kca.exists('equipment_panel', 'shipswitcher|4_slot_ship.png',cached=True):
                Log.log_debug(f"4 slot ship")
                kca_u.kca.click('4_slot_unload_equipment') 
            else: 
                Log.log_debug(f"5 slot ship")
                kca_u.kca.click('5_slot_unload_equipment') 
                
            kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
            
            if ship.slot_ex != None and \
               ship.slot_ex != Equipment():
                Log.log_debug(f"reinforce slot ship")
                kca_u.kca.click('reinforce_slot_unload_equipment')

            kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
            
            api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True)
            if api_result != {}:
                break
            else:
                Log.log_error(f"Something goes wrong, skipping this round...")
                
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
                break
            
        return True

    
    def unload_fleet_equipment(self, fleet_id, needed_load = False):
        """
        unload a fleet in the specified fleet, assume nav in equipment page already
            input: fleet_id: int, starts from 1
        """
        
        kca_u.kca.wait("left", f"nav|side_menu_equipment_active.png")
        while True:
            kca_u.kca.click_existing("upper_left", f"fleet|fleet_{fleet_id}.png")
            if  kca_u.kca.exists("upper_left", f"fleet|fleet_{fleet_id}_active.png"):
                break
            kca_u.kca.sleep(1)
            
        fleet_size = len(flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids)
        
        for i in range(fleet_size):
        
            Log.log_debug(f"unload the {i+1} ship")
            kca_u.kca.click('ship_'+ str(i + 1)) 
            
            if needed_load == True:
                #unload a ship to update equipment list
                kca_u.kca.click('1_slot_equipment') 
                
                ssw.ship_switcher.select_replacement_row(row_idx=randrange(10), mode= "equipment")

                kca_u.kca.click_existing(
                    'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')
                kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True, timeout=30)
                needed_load = False
            
            while True:
                
                # @todo do not rely on image, use ship api instead
                if kca_u.kca.exists('equipment_panel', 'shipswitcher|1_slot_ship.png'):
                    Log.log_debug(f"1 slot ship")
                    kca_u.kca.click('1_slot_unload_equipment')
                elif kca_u.kca.exists('equipment_panel', 'shipswitcher|2_slot_ship.png',cached=True):
                    Log.log_debug(f"2 slot ship")
                    kca_u.kca.click('2_slot_unload_equipment') 
                elif kca_u.kca.exists('equipment_panel', 'shipswitcher|3_slot_ship.png',cached=True):
                    Log.log_debug(f"3 slot ship")
                    kca_u.kca.click('3_slot_unload_equipment') 
                elif kca_u.kca.exists('equipment_panel', 'shipswitcher|4_slot_ship.png',cached=True):
                    Log.log_debug(f"4 slot ship")
                    kca_u.kca.click('4_slot_unload_equipment') 
                else: 
                    Log.log_debug(f"5 slot ship")
                    kca_u.kca.click('5_slot_unload_equipment') 
                    
                kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True)
                
                if flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ships[i].slot_ex != None and \
                   flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ships[i].slot_ex != Equipment():
                    Log.log_debug(f"reinforce slot ship")
                    kca_u.kca.click('reinforce_slot_unload_equipment')
                    kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                    api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True)
                
                if api_result != {}:
                    break
                else:
                    Log.log_error(f"Something goes wrong, skipping this round...")
                    
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
                    break


    def _load_equipment(self, fleet_id, fleet : Fleet):

        nav.navigate.to('home')

        load_ship_id = fleet.ship_ids
        
        if flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ship_ids != \
            fleet.ship_ids:
            Log.log_error(f"fleet {fleet_id} ship ids does not match, looks like ship load is failed, exiting...")
            exit(1)

        nav.navigate.to('equipment')
        
        kca_u.kca.wait("left", f"nav|side_menu_equipment_active.png")
        while True:
            kca_u.kca.click_existing("upper_left", f"fleet|fleet_{fleet_id}.png")
            if  kca_u.kca.exists("upper_left", f"fleet|fleet_{fleet_id}_active.png"):
                break
            kca_u.kca.sleep(1)
        
        for i in range(fleet.size):

            if fleet.ships[i].equipment_ids == flt.fleets.fleets[flt.fleets.ACTIVE_FLEET_KEY][fleet_id].ships[i].equipment_ids:
                Log.log_debug(f"equipment for ship {load_ship_id[i]} is already loaded")
                continue
            
            Log.log_debug(f"load the {i+1} ship")
            
            if i+1 == 7:
                next_region = Region(
                    kca_u.kca.game_x + 262,
                    kca_u.kca.game_y + 676,
                    32, 25)
                kca_u.kca.click(next_region)
                kca_u.kca.click('ship_'+ str(6)) 
            else:
                kca_u.kca.click('ship_'+ str(i + 1))

            ssw.ship_switcher.current_page = 1
            
            first_load = True
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
                ssw.ship_switcher.select_replacement_row(row_idx=row_id, mode= "equipment")
                kca_u.kca.click_existing(
                    'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')
                kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True, timeout=30)
                
            if fleet.ships[i].slot_ex != None and \
               fleet.ships[i].slot_ex.model_id != Equipment().model_id: 
                    
                kca_u.kca.click('reinforce_slot_equipment') 
                
                reinforce_equipment_list = equ.equipment.get_reinforce_equipment_list(fleet.ships[i])

                row_id = next((j for j, equipment in enumerate(reinforce_equipment_list) \
                    if equipment.production_id == fleet.ships[i].slot_ex.production_id), -1)
                
                if row_id == -1:
                    Log.log_error(f"Cannot find equipment {fleet.ships[i].slot_ex.name} \
                        with production id:{fleet.ships[i].slot_ex.production_id}, did you scrapped it?")
                    
                    exit(1)
                    
                ssw.ship_switcher.select_replacement_row(row_idx=row_id, ship=fleet.ships[i], mode= ssw.ship_switcher.REINFORCEMENT_MODE)

                kca_u.kca.click_existing(
                    'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')
                kca_u.kca.wait('lower', 'shipswitcher|equipment_panel.png')
                api_result = api.api.update_from_api({KCSAPIEnum.FREE_EQUIPMENT}, need_all=True, timeout=30)

        return True


        
fleet_switcher = FleetSwitcherCore()
