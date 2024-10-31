import curses
import json

import cui.util as util

from cui.macro import *

expedition_set = None

def init():
    # open the file for reading
    with open('data/expedition/expedition_preset.json') as f:
        # parse the JSON data using json.load()
        global expedition_set
        expedition_set = json.load(f)
    f.close()

def pop_up_menu(stdscr, panel, active_expset):

    x_center, y_center = util.get_center_str_location(panel, "EXP SET")
    panel.addstr(0, x_center, "EXP SET", curses.color_pair(LOG))

    global expedition_set
    active_id = 0 
    for i, expset in enumerate(expedition_set):
        if expset == active_expset:
            active_id = i

    while 1:
        row_count = len(expedition_set)
        for i, expset in enumerate(expedition_set):
            x_center, y_center = util.get_center_str_location(panel, expset)
            if i == active_id:
                active_expset = expset
                panel.addstr(i + y_center - int(row_count/2), x_center, expset, curses.color_pair(LOG_GREEN))
            else:
                panel.addstr(i + y_center - int(row_count/2), x_center, expset, curses.color_pair(LOG))

        panel.refresh()

        # Wait for next input
        key = stdscr.getch()

        if key == curses.KEY_DOWN or key == ord('j'):
            if active_id < len(expedition_set) - 1:
                active_id += 1
        elif key == curses.KEY_UP or key == ord('k'):
            if active_id > 0:
                active_id -= 1
        elif key == KEY_ENTER:
            break

    panel.clear()
    panel.border()

    active_preset = None

    if active_expset == "auto":
        active_preset = "auto"
    
    elif active_expset == "disable":
        active_preset = "disable"
    
    else:
        x_center, y_center = util.get_center_str_location(panel, "AUTO FLEET ASSIGN?")
        panel.addstr(0, x_center, "AUTO FLEET ASSIGN?", curses.color_pair(LOG))

        fleet_mode = ["disable", "auto"]
        cur_mode = 0
        while 1:
            for i, mode in enumerate(fleet_mode):
                if  cur_mode == i:
                    color = curses.color_pair(LOG_GREEN)
                else:
                    color = curses.color_pair(LOG)

                x_center, y_center = util.get_center_str_location(panel, mode)
                panel.addstr(y_center + i - 1, x_center, mode, color)
            panel.refresh()

            # Wait for next input
            key = stdscr.getch()
            if key == curses.KEY_DOWN or key == ord('j'):
                if cur_mode < len(fleet_mode) - 1:
                    cur_mode += 1
            elif key == curses.KEY_UP or key == ord('k'):
                if cur_mode > 0:
                    cur_mode -= 1
            elif key == KEY_ENTER:
                active_preset = fleet_mode[cur_mode]
                break
        
    return active_expset, active_preset

def get_current_exp_set(config):

    global expedition_set
    for preset in expedition_set:
        if  config["expedition.fleet_2"] == expedition_set[preset][0] and \
            config["expedition.fleet_3"] == expedition_set[preset][1] and \
            config["expedition.fleet_4"] == expedition_set[preset][2]:
            return preset
        
    if  config["expedition.fleet_2"] == ["active"] and \
        config["expedition.fleet_3"] == ["active"] and \
        config["expedition.fleet_4"] == ["active"] :
        return "active"
    
    elif  config["expedition.fleet_2"] == ["passive"] and \
          config["expedition.fleet_3"] == ["passive"] and \
          config["expedition.fleet_4"] == ["passive"] :
        return "passive"
    
    elif  config["expedition.fleet_2"] == ["overnight"] and \
          config["expedition.fleet_3"] == ["overnight"] and \
          config["expedition.fleet_4"] == ["overnight"] :
        return "overnight"
        
    return 'undefine'

def get_current_fleet(config):

    if  config["expedition.fleet_preset"] == "auto":
        return 'auto'
    return 'disable'

def set_config(config, expset, fleet_mode):
    global expedition_set

    if fleet_mode == "disable":
        config["expedition.fleet_preset"] = None
        config["expedition.fleet_2"] = expedition_set[expset][0]
        config["expedition.fleet_3"] = expedition_set[expset][1]
        config["expedition.fleet_4"] = expedition_set[expset][2]

    elif fleet_mode == "auto":
        config["expedition.fleet_preset"] = 'auto'

        if   expset == "active"\
            or expset == "passive"\
            or expset == "overnight":
            config["expedition.fleet_2"] = [expset]
            config["expedition.fleet_3"] = [expset]
            config["expedition.fleet_4"] = [expset]
        else:
            config["expedition.fleet_2"] = expedition_set[expset][0]
            config["expedition.fleet_3"] = expedition_set[expset][1]
            config["expedition.fleet_4"] = expedition_set[expset][2]

    return
