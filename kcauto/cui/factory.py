import curses

import cui.util as util
from cui.macro import *
from util.json_data import JsonData

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

SECRETARY_MODE_ID = 1
SECRETARY_MODE_TYPE = 2

MAX_QUEST_COL = 16

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

recipe_preset = {}
recipe = {}
secretary = {}

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
            file = open(RECIPE_PRESET_CONSTRUCT, 'r', encoding='utf-8')
        except FileNotFoundError:
        
            template_file = open(RECIPE_PRESET_CONSTRUCT_TEMPLATE, 'r', encoding='utf-8')
            #create preset file from template
            file = open(RECIPE_PRESET_CONSTRUCT, 'w', encoding='utf-8')
            file.write(template_file.read())
            template_file.close()
            file.close()
        
    if recipe_preset[DEVELOP_TAB] == []:
        try:
            file = open(RECIPE_PRESET_DEVELOP, 'r', encoding='utf-8')
        except FileNotFoundError:
            template_file = open(RECIPE_PRESET_DEVELOP_TEMPLATE, 'r', encoding='utf-8')
            #create preset file from template
            file = open(RECIPE_PRESET_DEVELOP, 'w', encoding='utf-8')
            file.write(template_file.read())
            template_file.close()
            file.close()
            
    recipe_preset[CONSTRUCT_TAB] = JsonData.load_json(RECIPE_PRESET_CONSTRUCT)
    recipe_preset[DEVELOP_TAB] = JsonData.load_json(RECIPE_PRESET_DEVELOP)
    
    current_tab = CONSTRUCT_TAB 
    current_active = TOP_MENU 
    curser = [1, 0]
    
    height, width = panel.getmaxyx()
    
    tab_height = 1
    secretary_height = 2
    resource_height = min((height - (tab_height + secretary_height)), 15)
    y_offset = 0
    
    row = [0, tab_height, tab_height + secretary_height]
    
    #read current quest status from config
    recipe[CONSTRUCT_TAB] = config["factory.build_recipe"]
    recipe[DEVELOP_TAB] = config["factory.develop_recipe"]
    
    for tab in TAB_ORDER:
        for i in range(len(recipe[tab])):
            recipe[tab][i] = int_to_list(recipe[tab][i], 4)
            
    secretary[CONSTRUCT_TAB] = int_to_list(config["factory.build_secretary"], 7)
    secretary[DEVELOP_TAB] = int_to_list(config["factory.develop_secretary"], 7)
    
    if secretary[CONSTRUCT_TAB] == [0,0,0,0,0,0,0]:
        secretary[CONSTRUCT_TAB] = 'on-hand'
    if secretary[DEVELOP_TAB] == [0,0,0,0,0,0,0]:
        secretary[DEVELOP_TAB] = 'on-hand'
        
    tab_col = [width//2//2 - len(" construct ")//2, width//2 + width//2//2 - len(" develop ")//2]
    
    x_secretary, y_secretary = util.get_center_str_location(panel, "Secretary ship XXXX XXXXXXX")
    secretary_col = [x_secretary, x_secretary + len("Secretary ship "), x_secretary + len("Secretary ship XXXX ")]
    
    x_recipe, y_recipe = util.get_center_str_location(panel, "PRESETNAME  XAMMOX XXXX  XBAUXITEX XXXX")
    recipe_col = [x_recipe, 
                  x_recipe + len("PRESETNAME    "), 
                  x_recipe + len("PRESETNAME    XAMMOX "), 
                  x_recipe + len("PRESETNAME    XAMMOX XXXX  "), 
                  x_recipe + len("PRESETNAME    XAMMOX XXXX  XBAUXITEX ")]
    
    secretary_mode = SECRETARY_MODE_ID
    
    while True:
        
        panel.clear()
        panel.border()
        panel.addstr(row[0], tab_col[0], 
                    ("<" if curser[CURSER_Y] == 0 and current_tab == CONSTRUCT_TAB else " ")+"Construct"+(">" if curser[CURSER_Y] == 0 and current_tab == CONSTRUCT_TAB else " "),
                    curses.color_pair(CONSTRUCT + (COLOR_REVERT * (int(current_tab == CONSTRUCT_TAB)))))
        panel.addstr(row[0], tab_col[1], 
                    ("<" if curser[CURSER_Y] == 0 and current_tab == DEVELOP_TAB else " ")+"Develop"+(">" if curser[CURSER_Y] == 0 and current_tab == DEVELOP_TAB else " "),
                    curses.color_pair(DEVELOP + (COLOR_REVERT * (int(current_tab == DEVELOP_TAB)))))
        
        panel.addstr(row[1] + 1, secretary_col[0], "Secretary ship ", curses.color_pair(LOG))
        
        panel.addstr(row[1] + 1, secretary_col[1], " ID ", curses.color_pair(LOG))
        
        if current_active == SECRETARY_MENU:
            for i in range(7):
                if curser[CURSER_Y] == 1 and i == curser[CURSER_X]:
                    panel.addstr(row[1] + 0, secretary_col[2] + i, str((secretary[current_tab][i] +9) % 10), curses.color_pair(LOG))
                    panel.addstr(row[1] + 1, secretary_col[2] + i, str(secretary[current_tab][i]), curses.color_pair(LOG_GREEN))
                    panel.addstr(row[1] + 2, secretary_col[2] + i, str((secretary[current_tab][i] +1) % 10), curses.color_pair(LOG))
                else:    
                    panel.addstr(row[1] + 1, secretary_col[2] + i, str(secretary[current_tab][i]), curses.color_pair(LOG))
        else:
            
            if curser[CURSER_Y] == 1:
                panel.addstr(row[1] + 1, secretary_col[2], str(list_to_int(secretary[current_tab])), curses.color_pair(LOG_GREEN))
            else:
                panel.addstr(row[1] + 1, secretary_col[2], str(list_to_int(secretary[current_tab])), curses.color_pair(LOG))
        
        for recipe_idx, preset in enumerate(recipe_preset[current_tab]):
            
            if recipe_idx < (y_offset * -1):
                continue
            
            if recipe_idx > resource_height - y_offset - 3:
                break
            
            if curser[CURSER_Y] == recipe_idx + 2 and curser[CURSER_X] == 0:
                panel.addstr(row[2] + 1 + recipe_idx + y_offset, recipe_col[0], preset, curses.color_pair(LOG_GREEN))
            else:
                panel.addstr(row[2] + 1 + recipe_idx + y_offset, recipe_col[0], preset, curses.color_pair(LOG))
        
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
            panel.addstr(row[2] + row_local_offset + 1, recipe_col[col_offset], " "+RESOURCE_DISPLAY_NAME[resource]+" ", curses.color_pair(color))
        
            if current_active == resource:    
                for i in range(4):
                    if i == curser[CURSER_X]:
                        panel.addstr(row[2] + row_local_offset + 0, recipe_col[col_offset +1] + i, str((recipe[current_tab][resource_idx][i] +9) % 10), curses.color_pair(LOG))
                        panel.addstr(row[2] + row_local_offset + 1, recipe_col[col_offset +1] + i, str(recipe[current_tab][resource_idx][i]), curses.color_pair(LOG_GREEN))
                        panel.addstr(row[2] + row_local_offset + 2, recipe_col[col_offset +1] + i, str((recipe[current_tab][resource_idx][i] +1) % 10), curses.color_pair(LOG))
                    else:    
                        panel.addstr(row[2] + row_local_offset + 1, recipe_col[col_offset +1] + i, str(recipe[current_tab][resource_idx][i]), curses.color_pair(LOG))
            else:
                if focus == resource:
                    panel.addstr(row[2] + row_local_offset + 1, recipe_col[col_offset +1], str(list_to_int(recipe[current_tab][resource_idx])).rjust(4, " "), curses.color_pair(LOG_GREEN))
                else:
                    panel.addstr(row[2] + row_local_offset + 1, recipe_col[col_offset +1], str(list_to_int(recipe[current_tab][resource_idx])).rjust(4, " "), curses.color_pair(LOG))
               
        
        panel.refresh()

        # Wait for next input
        key = stdscr.getch()
        
        if key == curses.KEY_DOWN or key == ord('j'):
            if current_active == TOP_MENU:
                if curser[CURSER_X] != 0:
                    if curser[CURSER_Y] < 3:
                        curser[CURSER_Y] += 1
                else:
                    if curser[CURSER_Y] < 1:
                        curser[CURSER_Y] += 1
                    elif curser[CURSER_Y] < recipe_preset[current_tab].__len__() + 1:
                        curser[CURSER_Y] += 1
                    y_offset = min(y_offset, (resource_height-2) - (curser[CURSER_Y] -2 +1) )
            elif current_active == SECRETARY_MENU:
                secretary[current_tab][curser[CURSER_X]] = (secretary[current_tab][curser[CURSER_X]] + 1) %10
            elif current_active == FUEL_MENU or current_active == AMMO_MENU or current_active == STEEL_MENU or current_active == BAUXITE_MENU:
                recipe[current_tab][RESOURCE_ORDER.index(current_active)][curser[CURSER_X]] \
                    = (recipe[current_tab][RESOURCE_ORDER.index(current_active)][curser[CURSER_X]] + 1) %10
                
        elif key == curses.KEY_UP or key == ord('k'):
            if current_active == TOP_MENU:
                if curser[CURSER_Y] > 0:
                    curser[CURSER_Y] -= 1
                    if curser[CURSER_Y] >1 and curser[CURSER_X] == 0:
                        y_offset = max(y_offset, -(curser[CURSER_Y] -2))
            elif current_active == SECRETARY_MENU:
                secretary[current_tab][curser[CURSER_X]] = (secretary[current_tab][curser[CURSER_X]] + 9) %10
            elif current_active == FUEL_MENU or current_active == AMMO_MENU or current_active == STEEL_MENU or current_active == BAUXITE_MENU:
                recipe[current_tab][RESOURCE_ORDER.index(current_active)][curser[CURSER_X]] \
                    = (recipe[current_tab][RESOURCE_ORDER.index(current_active)][curser[CURSER_X]] + 9) %10
                    
        elif key == curses.KEY_RIGHT or key == ord('l'):
            
            if current_active == TOP_MENU:
                if curser[CURSER_Y] == 0:
                    if current_tab != TAB_ORDER[-1]:
                        current_tab = TAB_ORDER[TAB_ORDER.index(current_tab)+1]
                        curser[CURSER_X] = 1
                else:
                    if curser[CURSER_X] < 2:
                        if curser[CURSER_X] == 0:
                            curser[CURSER_Y] = 2
                        curser[CURSER_X] += 1
                        
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
                else:
                        
                    
                    if curser[CURSER_X] != 0:
                        if curser[CURSER_X] == 1:
                            curser[CURSER_Y] = 2 - y_offset
                        curser[CURSER_X] -= 1
            elif current_active == SECRETARY_MENU:
                if curser[CURSER_X] > 0:
                    curser[CURSER_X] -= 1
            elif current_active == FUEL_MENU or current_active == AMMO_MENU or current_active == STEEL_MENU or current_active == BAUXITE_MENU:
                if curser[CURSER_X] > 0:
                    curser[CURSER_X] -= 1
            
        elif key == KEY_ENTER:
            if current_active == TOP_MENU:
                if curser[CURSER_Y] == 1:
                    current_active = SECRETARY_MENU
                    curser[CURSER_X] = 6
                    if secretary[current_tab] == 'on-hand':
                        secretary[current_tab] = [0,0,0,0,0,0,0]
                elif curser[CURSER_Y] >= 2:
                    if curser[CURSER_X] == 0:
                    
                        preset_idx = curser[CURSER_Y] -2
                        
                        recipe_name = ""
                        secretary_name = 0
                        if current_tab == CONSTRUCT_TAB:
                            recipe_name = "factory.build_recipe"
                            secretary_name = "factory.build_secretary"
                        elif current_tab == DEVELOP_TAB:
                            recipe_name = "factory.develop_recipe"
                            secretary_name = "factory.develop_secretary"
                        
                        secretary_int = list(recipe_preset[current_tab].items())[preset_idx][1][secretary_name]
                        if secretary_int == 0:
                            secretary[current_tab] = "on-hand"
                        else:
                            secretary[current_tab] = int_to_list(secretary_int, 7)
                            
                        recipe[current_tab] = [int_to_list(n,4) for n in list(recipe_preset[current_tab].items())[preset_idx][1][recipe_name]]
                    
                    else:
                        current_active = RESOURCE_ORDER[(curser[CURSER_Y]-2) + (curser[CURSER_X]-1)*2]
                        curser[CURSER_Y] = None
                        curser[CURSER_X] = 3
                    
            elif current_active == SECRETARY_MENU:
                current_active = TOP_MENU
                curser[CURSER_X] = 1
                curser[CURSER_Y] = 1
                if secretary[current_tab] == [0,0,0,0,0,0,0]:
                    secretary[current_tab] = 'on-hand'
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
    if secretary[CONSTRUCT_TAB] == 'on-hand':
        config["factory.build_secretary"] = 0
    else:   
        config["factory.build_secretary"] = list_to_int(secretary[CONSTRUCT_TAB])
        
    for resource in recipe[DEVELOP_TAB]:
        config["factory.develop_recipe"].append(list_to_int(resource))
    if secretary[DEVELOP_TAB] == 'on-hand':
        config["factory.develop_secretary"] = 0 
    else:
        config["factory.develop_secretary"] = list_to_int(secretary[DEVELOP_TAB])
    return
