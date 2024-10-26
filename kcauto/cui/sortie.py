import curses

import cui.util as util
from cui.macro import *

from fleet.noro6 import Noro6 

DISABLE = 0
AUTO = 1
NORMAL = 2

MAP = -1
WORLD = 1

world_list = {0:"", 1:"1", 2:"2", 3:"3", 4:"4", 5:"5", 6:"6", 7:"7", 8:"E", 9:""}
map_list = {0:"", 1:"1", 2:"2", 3:"3", 4:"4", 5:"5", 6:"6", 7:"7", 8:""}
mode_list = ["disable(akashi mode)", "auto", "normal"]
preset_list = {DISABLE:["disable", "akashi mode"], NORMAL:["disable", "auto", "1", "2", "3"]}

def pop_up_menu(stdscr, panel, cur_mode, sortie_map):

    global world_list, map_list
    
    mode_list = Noro6().get_variant("B-2-2")
    
    x_center, y_center = util.get_center_str_location(panel, "SORTIE MODE")
    panel.addstr(0, x_center, "SORTIE MODE", curses.color_pair(LOG))

    if cur_mode == NORMAL:
        mode_list[2] = sortie_map
    else:
        mode_list[2] = "1-1"

    while 1:

        for i, mode in enumerate(mode_list):
            if cur_mode == i:
                color = curses.color_pair(LOG_GREEN)
            else:
                color = curses.color_pair(LOG)

            x_center, y_center = util.get_center_str_location(panel, mode)
            panel.addstr(y_center + i - 1, x_center, mode, color)
        panel.refresh()

        # Wait for next input
        key = stdscr.getch()

        if key == curses.KEY_DOWN or key == ord('j'):
            if cur_mode < len(mode_list) - 1:
                cur_mode += 1
        elif key == curses.KEY_UP or key == ord('k'):
            if cur_mode > 0:
                cur_mode -= 1
        elif key == KEY_ENTER:
            break

    panel.clear()
    panel.border()

    cur_preset = 0
    akashi_mode = False
    if cur_mode == DISABLE:
        x_center, y_center = util.get_center_str_location(panel, "AKASHI ON?")
        panel.addstr(0, x_center, "AKASHI ON?", curses.color_pair(LOG))
        while 1:
            for i, preset in enumerate(preset_list[DISABLE]):
                if  cur_preset == i:
                    color = curses.color_pair(LOG_GREEN)
                else:
                    color = curses.color_pair(LOG)

                x_center, y_center = util.get_center_str_location(panel, preset)
                panel.addstr(y_center + i - 1, x_center, preset, color)
            panel.refresh()

            # Wait for next input
            key = stdscr.getch()
            if key == curses.KEY_DOWN or key == ord('j'):
                if cur_preset < len(preset_list[DISABLE]) - 1:
                    cur_preset += 1
            elif key == curses.KEY_UP or key == ord('k'):
                if cur_preset > 0:
                    cur_preset -= 1
            elif key == KEY_ENTER:
                if preset_list[DISABLE][cur_preset] == "disable":
                    pass
                elif preset_list[DISABLE][cur_preset] == "akashi mode":
                    akashi_mode = True
                break
        cur_preset = []
        sortie_map = ""
    elif cur_mode == AUTO:
        cur_preset = ["auto"]
        sortie_map = "auto"
    elif cur_mode == NORMAL:
        x_center, y_center = util.get_center_str_location(panel, "SORTIE MAP")
        panel.addstr(0, x_center, "SORTIE MAP", curses.color_pair(LOG))

        if len(sortie_map.split('-')) < 2:
            sortie_map = "1-1"

        map_or_world = WORLD

        for i in range(1, len(world_list) - 1):
            if world_list[i] == sortie_map.split('-')[0]:
                world_id = i
                break
        for i in range(1, len(map_list) - 1):
            if map_list[i] == sortie_map.split('-')[1]:
                map_id = i
                break

        while 1:
            x_center, y_center = util.get_center_str_location(panel, "XX-XX")
            sortie_map = world_list[world_id-1].rjust(2," ") + ' ' + map_list[map_id-1].ljust(2," ")
            panel.addstr(y_center - 1, x_center, sortie_map, curses.color_pair(LOG))
            if map_or_world == WORLD:
                panel.addstr(y_center + 0, x_center  , world_list[world_id+0].rjust(2," "), curses.color_pair(LOG_GREEN_ACTIVE))
                panel.addstr(y_center + 0, x_center+2, "-", curses.color_pair(LOG_GREEN))
                panel.addstr(y_center + 0, x_center+3, map_list[map_id+0].ljust(2," "), curses.color_pair(LOG_GREEN))
            elif map_or_world == MAP:
                panel.addstr(y_center + 0, x_center  , world_list[world_id+0].rjust(2," "), curses.color_pair(LOG_GREEN))
                panel.addstr(y_center + 0, x_center+2, "-", curses.color_pair(LOG_GREEN))
                panel.addstr(y_center + 0, x_center+3, map_list[map_id+0].ljust(2," "), curses.color_pair(LOG_GREEN_ACTIVE))
            sortie_map = world_list[world_id+1].rjust(2," ") + ' ' + map_list[map_id+1].ljust(2," ")
            panel.addstr(y_center + 1, x_center, sortie_map, curses.color_pair(LOG))

            panel.refresh()

            # Wait for next input
            key = stdscr.getch()
            if key == curses.KEY_DOWN or key == ord('j'):
                if map_or_world == MAP:
                    if map_id < len(map_list) - 2:
                        map_id += 1
                elif map_or_world == WORLD:
                    if world_id < len(world_list) - 2:
                        world_id += 1
            elif key == curses.KEY_UP or key == ord('k'):
                if map_or_world == MAP:
                    if map_id > 1:
                        map_id -= 1
                elif map_or_world == WORLD:
                    if world_id > 1:
                        world_id -= 1
            elif key == curses.KEY_RIGHT or key == ord('l'):
                map_or_world = MAP 
            elif key == curses.KEY_LEFT  or key == ord('h'):
                map_or_world = WORLD
            elif key == KEY_ENTER:
                break


        sortie_map = world_list[world_id] + '-' + map_list[map_id]

        panel.clear()
        panel.border()

        x_center, y_center = util.get_center_str_location(panel, "SORTIE FLEET")
        panel.addstr(0, x_center, "SORTIE FLEET", curses.color_pair(LOG))
 
        cur_preset = 0
        if cur_mode == NORMAL:
            while 1:
                for i, preset in enumerate(preset_list[NORMAL]):
                    if  cur_preset == i:
                        color = curses.color_pair(LOG_GREEN)
                    else:
                        color = curses.color_pair(LOG)

                    x_center, y_center = util.get_center_str_location(panel, preset)
                    panel.addstr(y_center + i - len(preset_list[NORMAL])//2, x_center, preset, color)
                panel.refresh()

                # Wait for next input
                key = stdscr.getch()
                if key == curses.KEY_DOWN or key == ord('j'):
                    if cur_preset < len(preset_list[NORMAL]) - 1:
                        cur_preset += 1
                elif key == curses.KEY_UP or key == ord('k'):
                    if cur_preset > 0:
                        cur_preset -= 1
                elif key == KEY_ENTER:
                    if preset_list[NORMAL][cur_preset] == "disable":
                        cur_preset = []
                    elif preset_list[NORMAL][cur_preset] == "auto":
                        cur_preset = [preset_list[NORMAL][cur_preset]]
                    else:
                        cur_preset = [int(preset_list[NORMAL][cur_preset])]
                    break
             
    return sortie_map, cur_preset ,akashi_mode

def get_current_sortie_map(config):
    return config["combat.sortie_map"]

def get_current_sortie_mode(config):
    if   config["combat.enabled"] == False:
        return DISABLE
    elif config["combat.sortie_map"] == "auto":
        return AUTO
    else:
        return NORMAL

def set_config(config, sortie_map, preset):
    if sortie_map == "":
        config["combat.enabled"] = False 
        config["combat.sortie_map"] = "1-1"
    else:
        config["combat.enabled"] = True 
        config["combat.sortie_map"] = sortie_map

    config["combat.fleet_presets"] = preset
    return
