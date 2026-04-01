import curses

import cui.util as util
from cui.macro import *
from util.json_data import JsonData
from kca_enums.ship_types import ShipTypeEnum as _ShipTypeEnum

from fleet.noro6 import Noro6 
from config.macro import RECIPE_PRESET_CONSTRUCT, RECIPE_PRESET_DEVELOP, RECIPE_PRESET_CONSTRUCT_TEMPLATE, RECIPE_PRESET_DEVELOP_TEMPLATE

CONSTRUCT_TAB = 1
DEVELOP_TAB = 2

TOP_MENU = 1
SECRETARY_MENU = 2
PRESET_MENU = 3
FUEL_MENU = 4
AMMO_MENU = 5
STEEL_MENU = 6
BAUXITE_MENU = 7
SECRETARY_TYPE_MENU = 8

_EXCLUDED_TYPES = {'NA', 'EAO', 'SD', 'WILDCARD'}
SECRETARY_TYPE_OPTIONS = ['on-hand', 'ID'] + [
    t.name for t in _ShipTypeEnum if t.name not in _EXCLUDED_TYPES
]
_SEC_MODE_FIELD = 10  # " " + name.ljust(8) + "|< or >" — fixed display width

TAB_ORDER = [CONSTRUCT_TAB, DEVELOP_TAB]
RESOURCE_ORDER = [FUEL_MENU, AMMO_MENU, STEEL_MENU, BAUXITE_MENU]
RESOURCE_PANEL_LAYOUT = [
    [FUEL_MENU, STEEL_MENU],
    [AMMO_MENU, BAUXITE_MENU]
]

RESOURCE_DISPLAY_NAME = {
    FUEL_MENU: "Fuel",
    AMMO_MENU: "Ammo",
    STEEL_MENU: "Steel",
    BAUXITE_MENU: "Bauxite"
}

BOARDER_WIDTH = 1
COL_NEEDED_WIDTH = 5

CURSER_X = 0
CURSER_Y = 1

# Index as python list, [include:exclude]
TOP_TAB_ROW = 0
SECRETARY_ROW = TOP_TAB_ROW + 2
RESOURCE_ROW_START = SECRETARY_ROW + 2
RESOURCE_ROW_END = RESOURCE_ROW_START + 3

COMMENT_ROW_START = RESOURCE_ROW_END + 1
COMMENT_ROW_END = COMMENT_ROW_START + 2

RECIPE_ROW_START = RESOURCE_ROW_START


recipe_preset = {}
recipe = {}
secretary = {}    # mode per tab: 'on-hand' | 'ID' | ship-type name (e.g. 'DD')
secretary_id = {} # digit list [7] per tab — only used when mode == 'ID'
comment = {}      # comment string for the currently-loaded preset per tab

def int_to_list(n, length):
    ret = []
    while n > 0:
        ret.append(n % 10)
        n //= 10
    while len(ret) < length:
        ret.append(0)
    ret.reverse()
    return ret

def list_to_int(lst):
    if type(lst) != list:
        return lst
    ret = 0
    for n in lst:
        ret = ret * 10 + n
    return ret

def pop_up_menu(stdscr, panel, config):
    
    global recipe_preset
    recipe_preset[CONSTRUCT_TAB] = []
    recipe_preset[DEVELOP_TAB] = []
    if recipe_preset[CONSTRUCT_TAB] == []:
        try:
            recipe_preset[CONSTRUCT_TAB] = JsonData.load_json(RECIPE_PRESET_CONSTRUCT)
        except FileNotFoundError:
            JsonData.dump_json(JsonData.load_json(RECIPE_PRESET_CONSTRUCT_TEMPLATE), RECIPE_PRESET_CONSTRUCT)
            recipe_preset[CONSTRUCT_TAB] = JsonData.load_json(RECIPE_PRESET_CONSTRUCT)

    if recipe_preset[DEVELOP_TAB] == []:
        try:
            recipe_preset[DEVELOP_TAB] = JsonData.load_json(RECIPE_PRESET_DEVELOP)
        except FileNotFoundError:
            JsonData.dump_json(JsonData.load_json(RECIPE_PRESET_DEVELOP_TEMPLATE), RECIPE_PRESET_DEVELOP)
            recipe_preset[DEVELOP_TAB] = JsonData.load_json(RECIPE_PRESET_DEVELOP)
    
    current_tab = CONSTRUCT_TAB
    current_active = TOP_MENU
    curser = [1, 0]
    
    height, width = panel.getmaxyx()
    
    RECIPE_ROW_END =  height - 2
    
    
    recipe_y_offset = 0 #the id of the first recipe currently displayed
    
    
    #read current quest status from config
    recipe[CONSTRUCT_TAB] = config["factory.build_recipe"]
    recipe[DEVELOP_TAB] = config["factory.develop_recipe"]
    
    for tab in TAB_ORDER:
        for i in range(len(recipe[tab])):
            recipe[tab][i] = int_to_list(recipe[tab][i], 4)
            
    def _load_secretary(value):
        """Return (mode_str, id_digit_list) from a raw config value."""
        if isinstance(value, str) and value not in ('on-hand',):
            return value, [0, 0, 0, 0, 0, 0, 0]   # ship-type name
        if not isinstance(value, int) or value == 0:
            return 'on-hand', [0, 0, 0, 0, 0, 0, 0]
        return 'ID', int_to_list(value, 7)

    secretary[CONSTRUCT_TAB], secretary_id[CONSTRUCT_TAB] = _load_secretary(config["factory.build_secretary"])
    secretary[DEVELOP_TAB],   secretary_id[DEVELOP_TAB]   = _load_secretary(config["factory.develop_secretary"])

    comment[CONSTRUCT_TAB] = ""
    comment[DEVELOP_TAB]   = ""
        
    tab_col = [width//2//2 - len(" construct ")//2, width//2 + width//2//2 - len(" develop ")//2]
    
    x_secretary, y_secretary = util.get_center_str_location(
        panel, "Secretary ship " + "X" * _SEC_MODE_FIELD + "X" * 7)
    secretary_col = [
        x_secretary,                                        # "Secretary ship " start
        x_secretary + len("Secretary ship "),               # mode label start  (width: _SEC_MODE_FIELD)
        x_secretary + len("Secretary ship ") + _SEC_MODE_FIELD,  # ship-id digits start (width: 7)
    ]
    
    x_recipe, y_recipe = util.get_center_str_location(panel, "PRESETNAME  XAMMOX XXXX  XBAUXITEX XXXX")
    recipe_col = [x_recipe, 
                  x_recipe + len("PRESETNAME    "), 
                  x_recipe + len("PRESETNAME    XAMMOX "), 
                  x_recipe + len("PRESETNAME    XAMMOX XXXX  "), 
                  x_recipe + len("PRESETNAME    XAMMOX XXXX  XBAUXITEX ")]
    
    while True:
        
        panel.clear()
        panel.border()
        panel.addstr(TOP_TAB_ROW, tab_col[0], 
                    ("<" if curser[CURSER_Y] == 0 and current_tab == CONSTRUCT_TAB else " ")+"Construct"+(">" if curser[CURSER_Y] == 0 and current_tab == CONSTRUCT_TAB else " "),
                    curses.color_pair(CONSTRUCT + (COLOR_REVERT * (int(current_tab == CONSTRUCT_TAB)))))
        panel.addstr(TOP_TAB_ROW, tab_col[1], 
                    ("<" if curser[CURSER_Y] == 0 and current_tab == DEVELOP_TAB else " ")+"Develop"+(">" if curser[CURSER_Y] == 0 and current_tab == DEVELOP_TAB else " "),
                    curses.color_pair(DEVELOP + (COLOR_REVERT * (int(current_tab == DEVELOP_TAB)))))
        
        panel.addstr(SECRETARY_ROW, secretary_col[0], "Secretary ship ", curses.color_pair(LOG))
        
        # --- mode selector (type cycling) ---
        sec_mode = secretary[current_tab]
        mode_in_type_menu = (current_active == SECRETARY_TYPE_MENU)
        mode_focused = (current_active == TOP_MENU and curser[CURSER_Y] == 1 and (sec_mode != 'ID' or curser[CURSER_X] < 2))  # focused if on secretary row and either not in ID mode or not on the digit column
        if mode_in_type_menu:
            mode_label = f"<{sec_mode.ljust(8)}>"
            mode_color = curses.color_pair(LOG_GREEN)
        elif mode_focused:
            mode_label = f" {sec_mode.ljust(8)} "
            mode_color = curses.color_pair(LOG_GREEN)
        else:
            mode_label = f" {sec_mode.ljust(8)} "
            mode_color = curses.color_pair(LOG)
        panel.addstr(SECRETARY_ROW, secretary_col[1], mode_label, mode_color)

        # --- ship-ID digits (only visible when mode is 'ID') ---
        if sec_mode == 'ID':
            if current_active == SECRETARY_MENU:
                for i in range(7):
                    if i == curser[CURSER_X]:
                        panel.addstr(SECRETARY_ROW - 1, secretary_col[2] + i, str((secretary_id[current_tab][i] + 9) % 10), curses.color_pair(LOG))
                        panel.addstr(SECRETARY_ROW + 0, secretary_col[2] + i, str(secretary_id[current_tab][i]), curses.color_pair(LOG_GREEN))
                        panel.addstr(SECRETARY_ROW + 1, secretary_col[2] + i, str((secretary_id[current_tab][i] + 1) % 10), curses.color_pair(LOG))
                    else:
                        panel.addstr(SECRETARY_ROW , secretary_col[2] + i, str(secretary_id[current_tab][i]), curses.color_pair(LOG))
            else:
                id_focused = (current_active == TOP_MENU and curser[CURSER_Y] == 1 and curser[CURSER_X] == 2)
                id_color = curses.color_pair(LOG_GREEN if id_focused else LOG)
                panel.addstr(SECRETARY_ROW, secretary_col[2], str(list_to_int(secretary_id[current_tab])).rjust(7), id_color)
        
        for recipe_idx, preset in enumerate(recipe_preset[current_tab]):

            if recipe_idx < recipe_y_offset:
                continue

            row = recipe_idx - recipe_y_offset
            if row > RECIPE_ROW_END - RECIPE_ROW_START:
                break

            if curser[CURSER_Y] == row + 2 and curser[CURSER_X] == 0:
                panel.addstr(RECIPE_ROW_START + row, recipe_col[0], preset, curses.color_pair(LOG_GREEN))
            else:
                panel.addstr(RECIPE_ROW_START + row, recipe_col[0], preset, curses.color_pair(LOG))
        
        for resource_idx, resource in enumerate(RESOURCE_ORDER):
            
            focus = None
            if resource == FUEL_MENU:
                row_local_offset = 0
                col_offset = 1
                color = PVP
                if curser[CURSER_Y] == 2 and curser[CURSER_X] == 1:
                    focus = FUEL_MENU
                
            elif resource == AMMO_MENU:
                row_local_offset = 2
                col_offset = 1
                color = FACTORY
                if curser[CURSER_Y] == 3 and curser[CURSER_X] == 1:
                    focus = AMMO_MENU
            elif resource == STEEL_MENU:
                row_local_offset = 0
                col_offset = 3
                color = STEEL
                if curser[CURSER_Y] == 2 and curser[CURSER_X] == 2:
                    focus = STEEL_MENU
            elif resource == BAUXITE_MENU:
                row_local_offset = 2
                col_offset = 3
                color = REPAIR 
                if curser[CURSER_Y] == 3 and curser[CURSER_X] == 2:
                    focus = BAUXITE_MENU
            panel.addstr(RESOURCE_ROW_START + row_local_offset, recipe_col[col_offset], " "+RESOURCE_DISPLAY_NAME[resource]+" ", curses.color_pair(color))
        
            if current_active == resource:    
                for i in range(4):
                    if i == curser[CURSER_X]:
                        panel.addstr(RESOURCE_ROW_START + row_local_offset - 1, recipe_col[col_offset +1] + i, str((recipe[current_tab][resource_idx][i] +9) % 10), curses.color_pair(LOG))
                        panel.addstr(RESOURCE_ROW_START + row_local_offset + 0, recipe_col[col_offset +1] + i, str(recipe[current_tab][resource_idx][i]), curses.color_pair(LOG_GREEN))
                        panel.addstr(RESOURCE_ROW_START + row_local_offset + 1, recipe_col[col_offset +1] + i, str((recipe[current_tab][resource_idx][i] +1) % 10), curses.color_pair(LOG))
                    else:    
                        panel.addstr(RESOURCE_ROW_START + row_local_offset + 0, recipe_col[col_offset +1] + i, str(recipe[current_tab][resource_idx][i]), curses.color_pair(LOG))
            else:
                if focus == resource:
                    panel.addstr(RESOURCE_ROW_START + row_local_offset, recipe_col[col_offset +1], str(list_to_int(recipe[current_tab][resource_idx])).rjust(4, " "), curses.color_pair(LOG_GREEN))
                else:
                    panel.addstr(RESOURCE_ROW_START + row_local_offset, recipe_col[col_offset +1], str(list_to_int(recipe[current_tab][resource_idx])).rjust(4, " "), curses.color_pair(LOG))
               
        # --- comment area (right column only, below resource panel) ---
        # resource panel occupies row[2]+0 .. row[2]+4; comment goes just below
        comment_row_0 = COMMENT_ROW_START
        comment_row_1 = COMMENT_ROW_END - 1
        comment_x     = recipe_col[1]           # same left edge as resource panel
        comment_w     = width - comment_x - 1   # up to the right border

        display_comment = comment[current_tab]
        if current_active == TOP_MENU and curser[CURSER_X] == 0 and curser[CURSER_Y] >= 2:
            # Convert cursor Y position (visible row) to actual preset index using scroll offset.
            hover_visible_idx = curser[CURSER_Y] - 2
            hover_idx = hover_visible_idx + recipe_y_offset
            presets_list = list(recipe_preset[current_tab].items())
            if 0 <= hover_idx < len(presets_list):
                display_comment = presets_list[hover_idx][1].get("comment", "")

        if comment_row_0 < height - 1:
            panel.addstr(comment_row_0, comment_x,
                         display_comment[:comment_w].ljust(comment_w),
                         curses.color_pair(LOG))
        if comment_row_1 < height - 1:
            panel.addstr(comment_row_1, comment_x,
                         display_comment[comment_w:comment_w * 2].ljust(comment_w),
                         curses.color_pair(LOG))

        panel.refresh()
        key = stdscr.getch()
        
        if key == curses.KEY_DOWN or key == ord('j'):
            if current_active == TOP_MENU:
                if curser[CURSER_Y] == 0:
                    curser[CURSER_Y] = 1  
                    curser[CURSER_X] = 0
                elif curser[CURSER_Y] == 1:
                    curser[CURSER_Y] = 2
                    curser[CURSER_X] = 1
                elif curser[CURSER_Y] > 1:
                    if curser[CURSER_X] == 0:
                        recipe_idx_current = curser[CURSER_Y] - 2 + recipe_y_offset
                        if recipe_idx_current + 1 < len(recipe_preset[current_tab]):
                            visible_row = recipe_idx_current - recipe_y_offset
                            if visible_row < RECIPE_ROW_END - RECIPE_ROW_START :
                                curser[CURSER_Y] += 1
                            else:
                                recipe_y_offset += 1
                    else:
                        if curser[CURSER_Y] < 3:
                            curser[CURSER_Y] += 1
            elif current_active == SECRETARY_TYPE_MENU:
                idx = SECRETARY_TYPE_OPTIONS.index(secretary[current_tab])
                secretary[current_tab] = SECRETARY_TYPE_OPTIONS[(idx + 1) % len(SECRETARY_TYPE_OPTIONS)]
            elif current_active == SECRETARY_MENU:
                secretary_id[current_tab][curser[CURSER_X]] = (secretary_id[current_tab][curser[CURSER_X]] + 1) % 10
            elif current_active == FUEL_MENU or current_active == AMMO_MENU or current_active == STEEL_MENU or current_active == BAUXITE_MENU:
                recipe[current_tab][RESOURCE_ORDER.index(current_active)][curser[CURSER_X]] \
                    = (recipe[current_tab][RESOURCE_ORDER.index(current_active)][curser[CURSER_X]] + 1) %10
                
        elif key == curses.KEY_UP or key == ord('k'):
            if current_active == TOP_MENU:
                if curser[CURSER_Y] == 1:
                    curser[CURSER_Y] = 0
                    curser[CURSER_X] = 0
                elif curser[CURSER_Y] == 2:
                    
                    if curser[CURSER_X] == 0:
                        
                        recipe_idx_current = curser[CURSER_Y] - 2 + recipe_y_offset
                        if recipe_idx_current > 0:
                            visible_row = recipe_idx_current - recipe_y_offset
                            if visible_row >= 0:
                                recipe_y_offset -= 1
                        else:
                            curser[CURSER_Y] -= 1
                            curser[CURSER_X] = 0
                                    
                    else:
                        curser[CURSER_Y] -= 1
                        curser[CURSER_X] = 0
                    
                elif curser[CURSER_Y] > 2:
                    #when in preset list, move up will scroll up if cursor is on the first visible preset
                    curser[CURSER_Y] -= 1
            elif current_active == SECRETARY_TYPE_MENU:
                idx = SECRETARY_TYPE_OPTIONS.index(secretary[current_tab])
                secretary[current_tab] = SECRETARY_TYPE_OPTIONS[(idx - 1) % len(SECRETARY_TYPE_OPTIONS)]
            elif current_active == SECRETARY_MENU:
                secretary_id[current_tab][curser[CURSER_X]] = (secretary_id[current_tab][curser[CURSER_X]] + 9) % 10
            elif current_active == FUEL_MENU or current_active == AMMO_MENU or current_active == STEEL_MENU or current_active == BAUXITE_MENU:
                recipe[current_tab][RESOURCE_ORDER.index(current_active)][curser[CURSER_X]] \
                    = (recipe[current_tab][RESOURCE_ORDER.index(current_active)][curser[CURSER_X]] + 9) %10
                    
        elif key == curses.KEY_RIGHT or key == ord('l'):
            
            if current_active == TOP_MENU:
                if curser[CURSER_Y] == 0:
                    if current_tab != TAB_ORDER[-1]:
                        current_tab = TAB_ORDER[TAB_ORDER.index(current_tab)+1]
                        curser[CURSER_X] = 1
                elif curser[CURSER_Y] == 1:
                    if curser[CURSER_X] != 2:
                        # on secretary row: only reach digit-column when mode is ID
                        if secretary[current_tab] == 'ID':
                            curser[CURSER_X] = 2
                else:    
                    if curser[CURSER_X] == 0:
                        curser[CURSER_Y] = 2
                        curser[CURSER_X] += 1
                    elif curser[CURSER_X] < 2:
                        curser[CURSER_X] += 1
            elif current_active == SECRETARY_TYPE_MENU:
                idx = SECRETARY_TYPE_OPTIONS.index(secretary[current_tab])
                secretary[current_tab] = SECRETARY_TYPE_OPTIONS[(idx + 1) % len(SECRETARY_TYPE_OPTIONS)]
            elif current_active == SECRETARY_MENU:
                if curser[CURSER_X] < 6:
                    curser[CURSER_X] += 1
            elif current_active == FUEL_MENU or current_active == AMMO_MENU or current_active == STEEL_MENU or current_active == BAUXITE_MENU:
                if curser[CURSER_X] < 3:
                    curser[CURSER_X] += 1
                
        elif key == curses.KEY_LEFT or key == ord('h'):
            if current_active == TOP_MENU:
                if curser[CURSER_Y] == 0:
                    if current_tab != TAB_ORDER[0]:
                        current_tab = TAB_ORDER[TAB_ORDER.index(current_tab)-1]
                        curser[CURSER_X] = 1
                elif curser[CURSER_Y] == 1:
                    if curser[CURSER_X] != 0:
                        curser[CURSER_X] -= 1
                elif curser[CURSER_Y] > 1:
                    if curser[CURSER_X] != 0:
                        if curser[CURSER_X] == 1:
                            curser[CURSER_Y] = 2
                        curser[CURSER_X] -= 1
            elif current_active == SECRETARY_TYPE_MENU:
                idx = SECRETARY_TYPE_OPTIONS.index(secretary[current_tab])
                secretary[current_tab] = SECRETARY_TYPE_OPTIONS[(idx - 1) % len(SECRETARY_TYPE_OPTIONS)]
            elif current_active == SECRETARY_MENU:
                if curser[CURSER_X] > 0:
                    curser[CURSER_X] -= 1
            elif current_active == FUEL_MENU or current_active == AMMO_MENU or current_active == STEEL_MENU or current_active == BAUXITE_MENU:
                if curser[CURSER_X] > 0:
                    curser[CURSER_X] -= 1
            
        elif key == KEY_ENTER:
            if current_active == TOP_MENU:
                if curser[CURSER_Y] == 1:
                    if curser[CURSER_X] == 2 and secretary[current_tab] == 'ID':
                        # enter digit-edit mode for the ship-ID field
                        current_active = SECRETARY_MENU
                        curser[CURSER_X] = 6
                    else:
                        # enter type-cycling mode for the mode selector
                        current_active = SECRETARY_TYPE_MENU
                elif curser[CURSER_Y] >= 2:
                    if curser[CURSER_X] == 0:
                    
                        preset_idx = curser[CURSER_Y] - 2 + recipe_y_offset
                        
                        recipe_name = ""
                        secretary_name = 0
                        if current_tab == CONSTRUCT_TAB:
                            recipe_name = "factory.build_recipe"
                            secretary_name = "factory.build_secretary"
                        elif current_tab == DEVELOP_TAB:
                            recipe_name = "factory.develop_recipe"
                            secretary_name = "factory.develop_secretary"
                        
                        secretary_int = list(recipe_preset[current_tab].items())[preset_idx][1][secretary_name]
                        secretary[current_tab], secretary_id[current_tab] = _load_secretary(secretary_int)
                        comment[current_tab] = list(recipe_preset[current_tab].items())[preset_idx][1].get("comment", "")
                            
                        recipe[current_tab] = [int_to_list(n,4) for n in list(recipe_preset[current_tab].items())[preset_idx][1][recipe_name]]
                    
                    else:
                        current_active = RESOURCE_ORDER[(curser[CURSER_Y]-2) + (curser[CURSER_X]-1)*2]
                        curser[CURSER_Y] = None
                        curser[CURSER_X] = 3
                    
            elif current_active == SECRETARY_TYPE_MENU:
                current_active = TOP_MENU
                curser[CURSER_X] = 1
                curser[CURSER_Y] = 1
            elif current_active == SECRETARY_MENU:
                current_active = TOP_MENU
                curser[CURSER_X] = 2  # return focus to digit column
                curser[CURSER_Y] = 1
            elif current_active == FUEL_MENU or current_active == AMMO_MENU or current_active == STEEL_MENU or current_active == BAUXITE_MENU:
                curser[CURSER_X] = RESOURCE_ORDER.index(current_active)//2 +1
                curser[CURSER_Y] = RESOURCE_ORDER.index(current_active)%2 +2
                current_active = TOP_MENU
                
                    
        elif key == ord('f') or key == ord('"') or key == KEY_ESC or key == ord('q'):
            break
    return None

def set_config(config):
    config["factory.build_recipe"] = []
    config["factory.build_secretary"] = None
    config["factory.develop_recipe"] = []
    config["factory.develop_secretary"] = None
    
    for resource in recipe[CONSTRUCT_TAB]:
        config["factory.build_recipe"].append(list_to_int(resource))
    def _save_secretary(tab):
        mode = secretary[tab]
        if mode == 'on-hand':
            return 0
        if mode == 'ID':
            return list_to_int(secretary_id[tab])
        return mode  # ship-type name string

    config["factory.build_secretary"] = _save_secretary(CONSTRUCT_TAB)

    for resource in recipe[DEVELOP_TAB]:
        config["factory.develop_recipe"].append(list_to_int(resource))
    config["factory.develop_secretary"] = _save_secretary(DEVELOP_TAB)
    return
