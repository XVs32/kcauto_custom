import curses
import json

import cui.util as util

from cui.macro import *

expedition_preset = None

def init():
    # open the file for reading
    with open('data/expedition/expedition_preset.json') as f:
        # parse the JSON data using json.load()
        global expedition_preset
        expedition_preset = json.load(f)
    f.close()

def pop_up_menu(stdscr, panel, active_preset):

    x_center, y_center = util.get_center_str_location(panel, "EXP SET")
    panel.addstr(0, x_center, "EXP SET", curses.color_pair(LOG))

    global expedition_preset
    active_id = 0 
    for i, preset in enumerate(expedition_preset):
        if preset == active_preset:
            active_id = i

    while 1:
        for i, preset in enumerate(expedition_preset):
            if i == active_id:
                active_preset = preset
                panel.addstr(i + 1, 1, preset, curses.color_pair(LOG_GREEN))
            else:
                panel.addstr(i + 1, 1, preset, curses.color_pair(LOG))

        panel.refresh()

        # Wait for next input
        key = stdscr.getch()

        if key == curses.KEY_DOWN or key == ord('j'):
            if active_id < len(expedition_preset) - 1:
                active_id += 1
        elif key == curses.KEY_UP or key == ord('k'):
            if active_id > 0:
                active_id -= 1
        elif key == KEY_ENTER:
            break
        
    return active_preset

def get_current_preset(config):

    global expedition_preset
    for preset in expedition_preset:
        if  config["expedition.fleet_2"] == expedition_preset[preset][0] and \
            config["expedition.fleet_3"] == expedition_preset[preset][1] and \
            config["expedition.fleet_4"] == expedition_preset[preset][2]:
            return preset
        
    return 'undefine'

def set_config(config, preset):
    global expedition_preset

    config["expedition.fleet_2"] = expedition_preset[preset][0]
    config["expedition.fleet_3"] = expedition_preset[preset][1]
    config["expedition.fleet_4"] = expedition_preset[preset][2]
    return
