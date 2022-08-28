from pyvisauto import Region

import fleet.fleet_core as flt

import combat.combat_core as com
import config.config_core as cfg
import nav.nav as nav
import ships.ships_core as shp
import stats.stats_core as sts
import util.kca as kca_u
from constants import EXACT, NEAR_EXACT
from ship_switcher.ship_switch_rule import ShipSwitchRule
from util.logger import Log


class ShipSwitcherCore(object):
    rules = {}
    current_shipcomp_page = 1

    def __init__(self):
        Log.log_debug("Initializing Ship Switcher core.")
        self._intake_rules(cfg.config.ship_switcher.slots)

    def _intake_rules(self, slot_rules):
        self.rules = {}
        for slot_id in slot_rules:
            self.rules[slot_id] = ShipSwitchRule(slot_id, slot_rules[slot_id])

    @property
    def need_to_switch(self):
        if not cfg.config.ship_switcher.enabled or len(self.rules) == 0:
            return False
        if self._slots_to_switch:
            Log.log_msg("Need to switch ships.")
            return True
        return False

    @property
    def _slots_to_switch(self):
        slots_to_switch = []
        
        for slot_id in self.rules:
            rule = self.rules[slot_id]
            
            if rule.need_to_switch():
                replacement_idx, replacement_ship = (
                    self._find_replacement_ship(rule))
                if replacement_idx is not None:
                    slots_to_switch.append({
                        'slot_id': slot_id,
                        'replacement_idx': replacement_idx,
                        'replacement_ship': replacement_ship})
        return slots_to_switch
    
    """Check the specified slot only -- XVs32"""
    def _slot_to_switch(self, slot_id):
        slot_to_switch = None
        
        rule = self.rules[slot_id]
        
        if rule.need_to_switch():
            replacement_idx, replacement_ship = (
                self._find_replacement_ship(rule))
            if replacement_idx is not None:
                slot_to_switch={
                    'slot_id': slot_id,
                    'replacement_idx': replacement_idx,
                    'replacement_ship': replacement_ship}
        return slot_to_switch

    def goto(self):
        nav.navigate.to('fleetcomp')
        self.current_shipcomp_page = 1

    def switch_ships(self):
        
        flag = False
        
        """For all 6 slots -- XVs32"""
        for i in range(1,7): 
            slot_to_switch = self._slot_to_switch(i)
            
            if slot_to_switch is not None:
                
                flag = True
                
                slot_id = slot_to_switch['slot_id']
                replacement_idx = slot_to_switch['replacement_idx']
                replacement_ship = slot_to_switch['replacement_ship']
                
                """The rule says remove the ship in this slot -- XVs32"""
                if replacement_idx < 0:
                    j = len(flt.fleets.fleets[1].ship_data) - slot_id + 1
                    while j > 0:
                        self._select_switch_button(slot_id)
                        self._select_remove_button()
                        j = j-1
                    
                    """End the switching process since the slots after this slot are empty"""
                    break
                
                rule = self.rules[slot_id]
                Log.log_msg(f"Switching {rule.ship_in_slot} in Slot {slot_id}.")
                
                self._select_switch_button(slot_id)
                kca_u.kca.sleep(1)
                self._reset_shiplist()
                self._select_replacement_ship(replacement_idx, replacement_ship)
                kca_u.kca.sleep()
                if self._switch_ship(replacement_ship):
                    sts.stats.ship_switcher.ships_switched += 1
                    
        if flag is True:
            com.combat.set_next_sortie_time(override=True)
        

    def _find_replacement_ship(self, rule):
        
        """If the slot needs to be empty"""
        if rule.ship_meets_criteria(None):
            return (-1, None)
        
        for idx, ship in enumerate(self._local_ships_sorted_by_levels):
            if rule.ship_meets_criteria(ship):
                return (idx, ship)
        Log.log_debug("No available switch-in ship found.")
        return (None, None)

    def _select_switch_button(self, slot_id):
        zero_idx = slot_id - 1
        slot_button_region = Region(
            kca_u.kca.game_x + 550 + ((zero_idx % 2) * 513),
            kca_u.kca.game_y + 295 + ((zero_idx // 2) * 168),
            125, 55)
        kca_u.kca.click_existing(
            slot_button_region, 'shipswitcher|shiplist_button.png')
        kca_u.kca.wait_vanish(
            slot_button_region, 'shipswitcher|shiplist_button.png')
        kca_u.kca.r['top'].hover()
        
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

    def _select_replacement_ship(self, ship_idx, ship):
        
        """ship_idx // 10 gives 0 when ship_idx < 10, the "if" statement is not needed---XVs32"""
        """target_page = (ship_idx // 10) + 1 if ship_idx > 9 else 1"""
        target_page = (ship_idx // 10) + 1
        Log.log_msg(
            f"Selecting lvl{ship.level} {ship.name} "
            f"(pg{target_page}#{ship_idx}).")
        
        """Floor division gives 9 pages when ship count == 96, which should be 10 pages ---XVs32"""
        """tot_pages = shp.ships.current_ship_count // 10"""
        """Since "current_ship_count" could never goes under 1, this could be"""
        """tot_pages = (shp.ships.current_ship_count - 1) // 10 + 1"""
        """Which is a bit cleaner and faster"""
        tot_pages = shp.ships.current_ship_count // 10 + min(1, shp.ships.current_ship_count%10) 

        list_control_region = Region(
            kca_u.kca.game_x + 625, kca_u.kca.game_y + 655, 495, 45)
        kca_u.kca.sleep(0.5)
        nav.navigate_list.to_page(
            list_control_region, tot_pages, self.current_shipcomp_page,
            target_page, 'shipcomp')
        self.current_shipcomp_page = target_page
        
        
        shipcomp_list_region = Region(
            kca_u.kca.game_x + 590,
            kca_u.kca.game_y + 225 + (ship_idx % 10 * 43),
            435, 34)
        kca_u.kca.click(shipcomp_list_region)
        kca_u.kca.r['top'].hover()
        kca_u.kca.wait(
            'lower_right', 'shipswitcher|shiplist_shipswitch_button.png')

    def _switch_ship(self, ship):
        if kca_u.kca.click_existing(
                'lower_right', 'shipswitcher|shiplist_shipswitch_button.png',
                cached=True):
            kca_u.kca.r['top'].hover()
            kca_u.kca.wait('right', 'shipswitcher|shiplist_button.png')
            return True
        else:
            Log.log_debug("Could not switch to selected ship.")
        return False

    @property
    def _local_ships_sorted_by_levels(self):
        temp_list = sorted(
            [s for s in shp.ships.local_ships],
            key=lambda s: (s.sort_id, s.local_id))
        temp_list = sorted(
            [s for s in temp_list],
            key=lambda s: s.level, reverse=True)
        return temp_list

    @property
    def _local_ships_sorted_by_class(self):
        return sorted(
            [s for s in shp.ships.local_ships],
            key=lambda s: (s.sort_id, s.local_id))


ship_switcher = ShipSwitcherCore()
