import sys,os
import io
import signal
import curses
import json
import threading
import subprocess

import time

from cui.macro import *
import cui.expedition as exp
import cui.pvp as pvp
import cui.sortie as sortie
import cui.ship_switch as ship_switch
import cui.passive_repair as passive_repair
import cui.scheduler as scheduler
import cui.util as util

process = None
panels = None

config = None
active_exp_preset = 'active'

def init():
    
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    global config
    # open the file for reading
    try:
        with open('configs/config_cui.json', encoding='utf-8') as f:
            # Load configuration file values
            config = json.load(f)
        f.close()
    except FileNotFoundError:
        with open('data/config/config_cui_template.json', encoding='utf-8') as f:
            # Load configuration file values
            config = json.load(f)
        f.close()

    exp.init()

    curses.curs_set(0)

    resize_panel()

    # Start colors in curses
    curses.start_color()
    curses.init_pair(SORTIE,    curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(SCHEDULER, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    curses.init_pair(PVP,       curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(EXP,       curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(LOG,       curses.COLOR_WHITE, curses.COLOR_BLACK)

    curses.init_pair(SORTIE + len(panels),    curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(SCHEDULER + len(panels), curses.COLOR_WHITE, curses.COLOR_MAGENTA)
    curses.init_pair(PVP + len(panels),       curses.COLOR_WHITE, curses.COLOR_GREEN)
    curses.init_pair(EXP + len(panels),       curses.COLOR_WHITE, curses.COLOR_CYAN)
    curses.init_pair(LOG + len(panels),       curses.COLOR_BLACK, curses.COLOR_WHITE)

    curses.init_pair(LOG_RED,       curses.COLOR_RED,   curses.COLOR_BLACK)
    curses.init_pair(LOG_GREEN,     curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(LOG_YELLOW,    curses.COLOR_YELLOW,curses.COLOR_BLACK)
    curses.init_pair(LOG_CYAN,      curses.COLOR_CYAN,  curses.COLOR_BLACK)
    curses.init_pair(LOG_GREEN_ACTIVE,curses.COLOR_GREEN,  curses.COLOR_WHITE)


def resize_panel():
    if curses.LINES < 8:
        raise ValueError("Error: Window too small(make it taller)")
    if curses.COLS < 45:
        raise ValueError("Error: Window too small(make it wider)")

    # Define the sub-panels
    top = 0
    left = 0
    next_top = 2 * curses.LINES // 7 
    next_left = curses.COLS // 4
    expedition_panel = curses.newwin(next_top - top, next_left - left, top, left)
    top = next_top 
    left = 0
    next_top = (2 + 2) * curses.LINES // 7
    next_left = curses.COLS // 4
    sortie_panel = curses.newwin(next_top - top, next_left - left, top, left)
    top = next_top 
    left = 0 
    next_top = (2 + 2 + 2) * curses.LINES // 7
    next_left = curses.COLS // 4
    scheduler_panel = curses.newwin(next_top - top, next_left - left, top, left)
    top = next_top 
    left = 0
    next_top =  curses.LINES
    next_left = curses.COLS // 4
    pvp_panel = curses.newwin(next_top - top, next_left - left, top, left)

    top  = 0 
    left = next_left 
    next_top  = curses.LINES
    next_left = curses.COLS // 4
    log_panel = curses.newwin(curses.LINES, curses.COLS - (curses.COLS // 4), 0, curses.COLS // 4)

    # Turn on scrolling for the log window
    log_panel.scrollok(True)

    global panels
    # Define the panels list
    panels = {EXP:expedition_panel, SORTIE: sortie_panel, SCHEDULER: scheduler_panel, PVP: pvp_panel, LOG: log_panel}


def draw_menu(stdscr):

    init()

    k = 0

    # Clear and refresh the screen for a blank canvas
    stdscr.clear()
    stdscr.refresh()
    
    # Define the initial active panel
    active_panel = EXP

    
    kc_auto = threading.Thread()
    #kc_auto = kc_auto_kick_start(panels[LOG])

    # Loop where k is the last character pressed
    while (k != ord('q')):

        active_panel = get_next_active_panel(active_panel, k)

        # Set the background color for the active panel
        update_active_panel(active_panel)

        refresh_panel()
        
        if k == KEY_ENTER:
            kc_auto = open_pop_up(kc_auto, stdscr, active_panel)
            panels[LOG].redrawwin()
            k = 0
        elif k == KEY_ESC:
            util.signal_handler()
        elif k == curses.KEY_RESIZE:
            time.sleep(0.1)
            curses.update_lines_cols()
            time.sleep(0.1)
            resize_panel()
            time.sleep(0.1)
            update_active_panel(active_panel)
            refresh_panel()

            # Wait for next input
            k = stdscr.getch()
        else:
            # Wait for next input
            k = stdscr.getch()

def refresh_panel():

    global panels
    for panel in panels:
        if panel == LOG:
            continue
        # Refresh the sub-panels
        panels[panel].clear()
        panels[panel].refresh()

    for panel in panels:
        if panel == EXP:
            preset = exp.get_current_exp_set(config)
            util.print_string(panels[panel], 0, -1, preset)

            exp_fleet = exp.get_current_fleet(config)
            util.print_string(panels[panel], 0, 0, exp_fleet)

        elif panel == SORTIE:
            
            if config["combat.fleet_presets"] == []:
                sortie_fleet = ["disable"]
            else:
                sortie_fleet = config["combat.fleet_presets"]

            if config["combat.enabled"] == False:
                sortie_map = "disable"

                if  config["ship_switcher.enabled"] == True and \
                    config["ship_switcher.slots"] == ship_switch.AKASHI_SHIP_SWITCHER_SLOTS:
                    sortie_fleet = ["akashi"]
            else:
                sortie_map = config["combat.sortie_map"]

            util.print_string(panels[panel], 0, -1, str(sortie_map))

            string = ','.join(map(str, sortie_fleet))
            util.print_string(panels[panel], 0, 0, string)

        elif panel == SCHEDULER :
            end_time = scheduler.get_end_time(config)
            sortie_count = scheduler.get_sortie_count(config)
            util.print_string(panels[panel], 0, -1, end_time[0:2] + ":" + end_time[2:4])
            util.print_string(panels[panel], 0, 0, str(sortie_count))
        elif panel == PVP:
            if config["pvp.enabled"] == False:
                pvp_fleet = "disable"
            else:
                pvp_fleet = str(config["pvp.fleet_preset"])
            util.print_string(panels[panel], 0, 0, pvp_fleet)

        panels[panel].refresh()

def update_active_panel(active_panel):

    for panel in panels:
        if panel == active_panel:
            panels[panel].bkgd(curses.color_pair(panel + 5))
        else:
            panels[panel].bkgd(curses.color_pair(panel))

def open_pop_up(thread, stdscr, active_panel):

    global config
    util.pop_up_lock = True

    # Create the pop-up window
    height =  max(3 * curses.LINES // 5, 7)
    width = max(3 * curses.COLS // 7, 25)
    top = curses.LINES // 2 - height // 2 
    left = curses.COLS // 2 - width // 2
    popup_win = curses.newwin(height, width, top, left)
    popup_win.border()

    if active_panel == EXP :

        expset = exp.get_current_exp_set(config)
        expset, fleet_mode = exp.pop_up_menu(stdscr, popup_win, expset)
        exp.set_config(config, expset, fleet_mode)
    
    elif active_panel == PVP :

        preset = pvp.get_current_preset(config)
        preset = pvp.pop_up_menu(stdscr, popup_win, preset)
        pvp.set_config(config, preset)

    elif active_panel == SORTIE :

        cur_sortie_mode = sortie.get_current_sortie_mode(config)
        sortie_map = sortie.get_current_sortie_map(config)
        sortie_map, preset, akashi_mode = sortie.pop_up_menu(stdscr, popup_win, cur_sortie_mode, sortie_map)
        sortie.set_config(config, sortie_map, preset)

        if akashi_mode == True:
            ship_switch.set_config(config, ship_switch.AKASHI_SHIP_SWITCHER_SLOTS)
            passive_repair.set_config(config, 0)
        else:
            ship_switch.set_config(config, {})
            passive_repair.set_config(config, 2)

    elif active_panel == SCHEDULER :
        end_time = scheduler.get_end_time(config)
        sortie_count = scheduler.get_sortie_count(config)
        end_time, sortie_count = scheduler.pop_up_menu(stdscr, popup_win, end_time, sortie_count)
        scheduler.set_config(config, end_time, sortie_count)
    elif active_panel == LOG :

        isYes=False
        while 1:
            x, y = util.get_center_str_location(popup_win, "Reload config?")
            popup_win.addstr(y-1, x, "Reload config?", curses.color_pair(5))
            if isYes:
                x, y = util.get_center_str_location(popup_win, "Yes")
                popup_win.addstr(y, x, "Yes", curses.color_pair(12))
                x, y = util.get_center_str_location(popup_win, "No")
                popup_win.addstr(y + 1, x, "No", curses.color_pair(5))
            else:
                x, y = util.get_center_str_location(popup_win, "Yes")
                popup_win.addstr(y, x, "Yes", curses.color_pair(5))
                x, y = util.get_center_str_location(popup_win, "No")
                popup_win.addstr(y + 1, x, "No", curses.color_pair(12))
            popup_win.refresh()
            for panel in panels:
                # Refresh the sub-panels
                panels[panel].refresh()

            # Wait for next input
            key = stdscr.getch()

            if key == curses.KEY_DOWN or key == ord('j'):
                isYes = False
            elif key == curses.KEY_UP or key == ord('k'):
                isYes = True
            elif key == KEY_ENTER:
                if isYes == True:
                    # open the file for writing
                    with open('configs/config_cui.json', 'w', encoding='utf-8') as output:
                        # parse the JSON data using json.load()
                        json.dump(config, output, indent=4, sort_keys=True)
                    output.close()
                    
                    # send a SIGTERM signal to terminate the subprocess
                    if thread.is_alive() == True:
                        util.process.send_signal(subprocess.signal.SIGTERM)
                        thread.join()

                    thread = kc_auto_kick_start(panels[LOG])
                break

    util.pop_up_lock = False
    return thread

def get_next_active_panel(active_panel, key):

    if key == curses.KEY_DOWN or key == ord('j'):
        if active_panel == EXP:
            active_panel = SORTIE
        elif active_panel == SORTIE:
            active_panel = SCHEDULER
        elif active_panel == SCHEDULER:
            active_panel = PVP 
    elif key == curses.KEY_UP or key == ord('k'):
        if active_panel == SORTIE:
            active_panel = EXP 
        elif active_panel == SCHEDULER:
            active_panel = SORTIE
        elif active_panel == PVP:
            active_panel = SCHEDULER
    elif key == curses.KEY_RIGHT or key == ord('l'):
        if active_panel == EXP:
            active_panel = LOG
        elif active_panel == SORTIE:
            active_panel = LOG 
        elif active_panel == SCHEDULER:
            active_panel = LOG
        elif active_panel == PVP:
            active_panel = LOG
    elif key == curses.KEY_LEFT or key == ord('h'):
        if active_panel == LOG:
            active_panel = EXP 
        
    return active_panel

def kc_auto_kick_start(log_panel):
    # create a new thread
    kc_auto = threading.Thread(target=util.run_external_program,args=[log_panel])
    # Kill the child thread if parent is dead
    kc_auto.daemon = True 

    # start the thread
    kc_auto.start()
    return kc_auto

def main():
    signal.signal(signal.SIGINT, util.signal_handler)
    curses.wrapper(draw_menu)

if __name__ == "__main__":
    main()    