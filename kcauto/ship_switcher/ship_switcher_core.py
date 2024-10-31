from pyvisauto import Region

import fleet.fleet_core as flt

import api.api_core as api
from kca_enums.kcsapi_paths import KCSAPIEnum
import combat.combat_core as com
import config.config_core as cfg
import nav.nav as nav
import ships.equipment_core as equ 
import ships.ships_core as shp
import stats.stats_core as sts
import util.kca as kca_u
from constants import EXACT, NEAR_EXACT
from ship_switcher.ship_switch_rule import ShipSwitchRule
from util.logger import Log


class ShipSwitcherCore(object):
    rules = {}
    current_page = 1
    DUMMY = -1

    def __init__(self):
        Log.log_debug("Initializing Ship Switcher core.")
        self._intake_rules(cfg.config.ship_switcher.slots)

    def _intake_rules(self, slot_rules):
        
        self.rules = {}
        for slot_id in slot_rules:
            self.rules[slot_id] = ShipSwitchRule(slot_id, slot_rules[slot_id])


    def switch_slot_by_id(self, slot, ship_local_id):
        """
            method to switch a slot to a specified ship
            Args:
                slot(int): The slot to switch, index starts from one
                ship_local_id(int): The target ship production id
            @todo: track fleet ship_ids using API, not ship_local_id
        """

        # The slot has the specified ship already
        #@todo upper function has to handle the switched already detection
        #if len(flt.fleets.fleets[1].ship_ids) >= slot and ship_local_id == flt.fleets.fleets[1].ship_ids[slot-1]:
            #return

        if not self._select_switch_button(slot):
            return False

        if ship_local_id == -1:
            """Remove ship in this slot"""
            self._select_remove_button()
        else:
            ship_idx = self._get_ship_idx_by_local_id(ship_local_id)
            kca_u.kca.sleep(1)
            self._reset_shiplist()
            self.select_replacement_row(ship_idx)
            kca_u.kca.sleep(1)
            if not self._switch_ship():
                return False
        return True

    def switch_ships(self, switch_list):
        
        for switch_info in switch_list:
            
            """The rule says remove the ship in this slot -- XVs32"""
            if switch_info["idx"] < 0:
                j = len(flt.fleets.fleets[1].ship_data) - switch_info["slot_id"] + 1
                while j > 0:
                    self._select_switch_button(switch_info["slot_id"])
                    self._select_remove_button()
                    j = j-1
                """End the switching process since the slots after this slot are empty"""
                break

            self.switch_slot_by_id(switch_info["slot_id"], switch_info["ship"].production_id)

            """self._select_switch_button(switch_info["slot_id"])
            kca_u.kca.sleep(2)
            self._reset_shiplist()
            self._select_replacement_ship(switch_info["idx"], switch_info["ship"])
            kca_u.kca.sleep(2)
            if self._switch_ship():
                sts.stats.ship_switcher.ships_switched += 1
            else:
                not_fleet_region = Region(
                    kca_u.kca.game_x + 185,
                    kca_u.kca.game_y + 210,
                    330, 450)
                while not kca_u.kca.exists(
                    'right', 'shipswitcher|shiplist_button.png'):
                    kca_u.kca.click(not_fleet_region)
                    kca_u.kca.sleep(1)
                return False"""

        """Check if next combat possible, since new ship is switched in"""
        """Refresh home to update ship list"""
        if switch_list:
            com.combat.set_next_sortie_time(override=True)
            nav.navigate.to('refresh_home')
            api.api.update_from_api({KCSAPIEnum.PORT})
            

    def get_ship_switch_list(self):

        """slot_id, idx, ship"""
        switch_list = []
        
        if not cfg.config.ship_switcher.enabled or len(self.rules) == 0:
            return switch_list
        
        ship_list = self._local_ships_sorted_by_levels
        
        """For all 6 slots -- XVs32"""
        for i in range(1,7):
            
            rule = self.rules[i]
            
            if rule.is_switch_out():
                replacement_idx, replacement_ship = (
                    self._find_replacement_ship(rule, ship_list))

                if rule.ship_in_slot != None:
                    """If the slot needs to be empty"""
                    if rule.is_meet_criteria(None):
                        replacement_idx, replacement_ship = (-1, None)
                        
                if replacement_idx is not None:
                    
                    """Remove this ship from availble list"""
                    ship_list[replacement_idx] = self.DUMMY
                    
                    switch_list.append({
                        'slot_id': i,
                        'idx': replacement_idx,
                        'ship': replacement_ship})
                    
                    
        if switch_list:
            Log.log_msg("Need to switch ships.")
            
        return switch_list

    def _get_ship_idx_by_local_id(self, local_id = 0):

        ship_list = self._local_ships_sorted_by_levels
        
        for i in range(len(ship_list)):
            if ship_list[i].production_id == local_id:
                return i

        raise ValueError("Can not find the specified ship")

    def _find_replacement_ship(self, rule, ship_list):
        
        for idx, ship in enumerate(ship_list):
            
            if ship == self.DUMMY:
                continue
            
            if rule.is_meet_criteria(ship):
                return (idx, ship)
        Log.log_debug("No available switch-in ship found.")
        return (None, None)

    def goto(self):
        nav.navigate.to('fleetcomp')
        self.current_page = 1
        
    def _select_switch_button(self, slot_id):
        zero_idx = slot_id - 1
        slot_button_region = Region(
            kca_u.kca.game_x + 550 + ((zero_idx % 2) * 513),
            kca_u.kca.game_y + 295 + ((zero_idx // 2) * 168),
            125, 55)
        if kca_u.kca.exists(
            slot_button_region, 'shipswitcher|shiplist_button.png'):
            kca_u.kca.click_existing(
                slot_button_region, 'shipswitcher|shiplist_button.png')
        else:
            return False

        kca_u.kca.wait_vanish(
            slot_button_region, 'shipswitcher|shiplist_button.png')
        kca_u.kca.r['top'].hover()

        return True
        
    def _select_remove_button(self):
        slot_button_region = Region(
            kca_u.kca.game_x + 1100,
            kca_u.kca.game_y + 650,
            100, 50)
        kca_u.kca.click_existing(
            slot_button_region, 'shipswitcher|shiplist_shipremove_button.png')
        kca_u.kca.wait_vanish(
            slot_button_region, 'shipswitcher|shiplist_shipremove_button.png')
        kca_u.kca.r['top'].hover()

    def _reset_shiplist(self):
        if not kca_u.kca.exists(
                'upper_right', 'shipswitcher|shiplist_quick_tab_all.png',
                EXACT):
            kca_u.kca.click_existing(
                'upper_right', 'shipswitcher|shiplist_quick_tab_none.png',
                NEAR_EXACT, cached=True)
        while not kca_u.kca.exists(
                'upper_right', 'shipswitcher|shiplist_sort_level.png'):
            kca_u.kca.click_existing(
                'upper_right', 'shipswitcher|shiplist_sort_arrow.png',
                cached=True)
            kca_u.kca.sleep(0.1)

    def select_replacement_row(self, row_idx, ship = None, mode = "ship"):
        
        """ship_idx // 10 gives 0 when ship_idx < 10, the "if" statement is not needed---XVs32"""
        """target_page = (ship_idx // 10) + 1 if ship_idx > 9 else 1"""

        target_page = (row_idx // 10) + 1

        if mode == "ship":
            if ship == None:
                Log.log_msg(f"Selecting {row_idx}"
                            f"(From pg{self.current_page} to pg{target_page}).")
            else:
                Log.log_msg(
                    f"Selecting lvl{ship.level} {ship.name} "
                    f"(pg{target_page}#{row_idx}).")
        elif mode == "equipment":
            Log.log_msg(f"Selecting {row_idx}"
                        f"(From pg{self.current_page} to pg{target_page}).")
            pass
        
        """Floor division gives 9 pages when ship count == 96, which should be 10 pages ---XVs32"""
        """tot_pages = shp.ships.current_ship_count // 10"""
        """Since "current_ship_count" could never goes under 1, this could be"""
        """tot_pages = (shp.ships.current_ship_count - 1) // 10 + 1"""
        """Which is a bit cleaner and faster"""
        if mode == "ship":
            tot_pages = (shp.ships.ship_count -1) // 10 + 1
        elif mode == "equipment":
            tot_pages = (len(equ.equipment.equipment['free']) -1) // 10 + 1

        list_control_region = Region(
            kca_u.kca.game_x + 625, kca_u.kca.game_y + 655, 495, 45)
        kca_u.kca.sleep(0.5)

        if mode == "ship":
            offset_mode = 'shipcomp' 
        elif mode == "equipment":
            offset_mode = 'equipment' 
        nav.navigate_list.to_page(
            list_control_region, tot_pages, self.current_page,
            target_page, offset_mode)
        self.current_page = target_page
        
       
        if mode == "ship":
            row_region = Region(
                kca_u.kca.game_x + 590,
                kca_u.kca.game_y + 225 + (row_idx % 10 * 43),
                435, 34)
        elif mode == "equipment":
            row_region = Region(
                kca_u.kca.game_x + 590,
                kca_u.kca.game_y + 195 + 5 + (row_idx % 10 * 45),
                435, 34)

        kca_u.kca.click(row_region)
        kca_u.kca.r['top'].hover()
        if mode == "ship":
            kca_u.kca.wait(
                'lower_right', 'shipswitcher|shiplist_shipmenu.png')
        elif mode == "equipment":
            kca_u.kca.wait(
                'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')

    def _switch_ship(self):

        flag = False 
        retry = 0

        if kca_u.kca.click_existing(
                'lower_right', 'shipswitcher|shiplist_shipswitch_button.png', cached = True):
            kca_u.kca.r['top'].hover()
            while retry < 5:
                if kca_u.kca.exists('right', 'shipswitcher|shiplist_button.png'):
                    flag = True
                    break
                else:
                    retry += 1
                    kca_u.kca.sleep(1)
            
        if not flag:
            Log.log_warn("Could not switch to selected ship.")

        return flag

    @property
    def _local_ships_sorted_by_levels(self):
        
        temp_list = [value for key, value in sorted(shp.ships.ship_pool.items(), key=lambda item: (item[1].sort_id, item[1].production_id ))]

        #temp_list = sorted(
        #    [shp.ships.ship_pool[s] for s in shp.ships.ship_pool],
        #    key=lambda s: (shp.ships.ship_pool[s].sort_id, shp.ships.ship_pool[s].production_id))
        temp_list = sorted(
            [s for s in temp_list],
            key=lambda s: s.level, reverse=True)

        return temp_list

    @property
    def _local_ships_sorted_by_class(self):
        return sorted(
            [shp.ships.ship_pool[s] for s in shp.ships.ship_pool],
            key=lambda ship: (ship.sort_id, ship.production_id))

ship_switcher = ShipSwitcherCore()
