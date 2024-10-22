import curses

import cui.util as util

from cui.macro import *

DISABLE = 0
AUTO_MODE = 1
LIST_OFFSET = 1

def pop_up_menu(stdscr, panel, preset_id):
    

    x_center, y_center = util.get_center_str_location(panel, "PVP PRESET")
    panel.addstr(0, x_center, "PVP PRESET", curses.color_pair(LOG))
    
    if preset_id == 'auto':
        preset_id = AUTO_MODE
    elif preset_id != DISABLE:
        preset_id+=LIST_OFFSET

    while 1:
        
        for i in range(0, 5):

            if i == DISABLE:
                preset = "disable"
            elif i == AUTO_MODE:
                preset = "auto"
            else:
                preset = str(i-LIST_OFFSET)

            if i == preset_id:
                panel.addstr(i + 1, 1, preset, curses.color_pair(LOG_GREEN))
            else:
                panel.addstr(i + 1, 1, preset, curses.color_pair(LOG))
        
        panel.refresh()

        # Wait for next input
        key = stdscr.getch()

        if key == curses.KEY_DOWN or key == ord('j'):
            if preset_id < 4:
                preset_id += 1
        elif key == curses.KEY_UP or key == ord('k'):
            if preset_id > 0:
                preset_id -= 1
        elif key == KEY_ENTER:
            break
        
    return preset_id 

def get_current_preset(config):
    return config["pvp.fleet_preset"]

def set_config(config, preset):
    if preset == DISABLE:
        config["pvp.enabled"] = False 
        config["pvp.fleet_preset"] = 0
    elif preset == AUTO_MODE:
        config["pvp.enabled"] = True 
        config["pvp.fleet_preset"] = "auto" 
    else:
        config["pvp.enabled"] = True 
        config["pvp.fleet_preset"] = preset-LIST_OFFSET
    return
