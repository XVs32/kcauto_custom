import curses

from cui.macro import *

def pop_up_menu(stdscr, panel, preset_id):

    while 1:
        
        for i in range(0, 4):

            if i == 0:
                preset = "Disable"
            else:
                preset = str(i)

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
    if preset == 0:
        config["pvp.enabled"] = False 
        config["pvp.fleet_preset"] = 0
    else:
        config["pvp.enabled"] = True 
        config["pvp.fleet_preset"] = preset
    return
