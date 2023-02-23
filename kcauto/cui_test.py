import sys,os
import signal
import curses
import json
import threading
import subprocess

from cui.macro import *
import cui.expedition as exp
import cui.pvp as pvp

pop_up_lock = False
process = None
panels = None

config = None
active_exp_preset = 'active'

def init():
    global config
    # open the file for reading
    with open('configs/config.json') as f:
        # parse the JSON data using json.load()
        config = json.load(f)
    f.close()

    exp.init()

    curses.curs_set(0)

    # Define the sub-panels
    top = 0
    left = 0
    next_top = 1 * curses.LINES // 5 
    next_left = curses.COLS // 5
    expedition_panel = curses.newwin(next_top - top, next_left - left, top, left)
    top = next_top 
    left = 0
    next_top = 3 * curses.LINES // 5
    next_left = curses.COLS // 5
    sortie_panel = curses.newwin(next_top - top, next_left - left, top, left)
    top = next_top 
    left = 0 
    next_top = 4 * curses.LINES // 5
    next_left = curses.COLS // 5
    scheduler_panel = curses.newwin(next_top - top, next_left - left, top, left)
    top = next_top 
    left = 0
    next_top =  curses.LINES
    next_left = curses.COLS // 5
    pvp_panel = curses.newwin(next_top - top, next_left - left, top, left)

    top  = 0 
    left = next_left 
    next_top  = curses.LINES
    next_left = curses.COLS // 5
    log_panel = curses.newwin(curses.LINES, 4 * curses.COLS // 5, 0, curses.COLS // 5)

    log_panel.scrollok(True)

    global panels
    # Define the panels list
    panels = {EXP:expedition_panel, SORTIE: sortie_panel, SCHEDULER: scheduler_panel, PVP: pvp_panel, LOG: log_panel}

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


def draw_menu(stdscr):

    init()

    k = 0

    # Clear and refresh the screen for a blank canvas
    stdscr.clear()
    stdscr.refresh()
    
    # Define the initial active panel
    active_panel = EXP

    kc_auto = kc_auto_kick_start(panels[LOG])

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
            preset = exp.get_current_preset(config)
            print_string(panels[panel], 0, 0, preset)

        elif panel == SORTIE:
        #elif panel == sortie_panel:
            sortie_map = config["combat.sortie_map"]
            sortie_fleet = config["combat.fleet_presets"]

            print_string(panels[panel], 0, 0, str(sortie_map))

            string = ','.join(map(str, sortie_fleet))
            print_string(panels[panel], 0, 1, string)

        elif panel == PVP:
            if config["pvp.enabled"] == False:
                pvp_fleet = "Disable"
            else:
                pvp_fleet = str(config["pvp.fleet_preset"])
            print_string(panels[panel], 0, 0, pvp_fleet)

        panels[panel].refresh()

def update_active_panel(active_panel):

    for panel in panels:
        if panel == active_panel:
            panels[panel].bkgd(curses.color_pair(panel + 5))
        else:
            panels[panel].bkgd(curses.color_pair(panel))

def open_pop_up(thread, stdscr, active_panel):

    global config
    global pop_up_lock
    pop_up_lock = True

    # Create the pop-up window
    height =  3 * curses.LINES // 5 
    width = 3 * curses.COLS // 7
    top =  1 * curses.LINES // 5
    left =  2 * curses.COLS // 7
    popup_win = curses.newwin(height, width, top, left)
    popup_win.border()

    if active_panel == EXP :
        preset = exp.get_current_preset(config)
        preset = exp.pop_up_menu(stdscr, popup_win, preset)
        config = exp.set_config(config, preset)
    
    elif active_panel == PVP :
        preset = pvp.get_current_preset(config)
        preset = pvp.pop_up_menu(stdscr, popup_win, preset)
        config = pvp.set_config(config, preset)

    elif active_panel == LOG :

        isYes=False
        while 1:
            x, y = get_center_str_location(popup_win, "Reload config?")
            popup_win.addstr(y-1, x, "Reload config?", curses.color_pair(5))
            if isYes:
                x, y = get_center_str_location(popup_win, "Yes")
                popup_win.addstr(y, x, "Yes", curses.color_pair(12))
                x, y = get_center_str_location(popup_win, "No")
                popup_win.addstr(y + 1, x, "No", curses.color_pair(5))
            else:
                x, y = get_center_str_location(popup_win, "Yes")
                popup_win.addstr(y, x, "Yes", curses.color_pair(5))
                x, y = get_center_str_location(popup_win, "No")
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
                    with open('configs/config.json', 'w') as output:
                        # parse the JSON data using json.load()
                        json.dump(config, output, indent=4, sort_keys=True)
                    output.close()
                    
                    # send a SIGTERM signal to terminate the subprocess
                    process.send_signal(subprocess.signal.SIGTERM)
                    thread.join()

                    thread = kc_auto_kick_start(panels[LOG])
                break

    pop_up_lock = False
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


def get_center_str_location(window, string):

    height, width = window.getmaxyx()

    x_center = int((width // 2) - (len(string) // 2) - len(string) % 2)
    y_center = int( height// 2 )
    return x_center, y_center

def print_string(window, offset_x, offset_y, string):
    x, y = get_center_str_location(window, string)
    window.addstr(y + offset_y, x + offset_x, string)

def print_log(panel, string):
    if string[2:4] == "91": #Error
        panel.addstr(string[5:-5] + "\n", curses.color_pair(LOG_RED))
    elif string[2:4] == "92": #Status
        panel.addstr(string[5:-5] + "\n", curses.color_pair(LOG_GREEN))
    elif string[2:4] == "93": #Warnning
        panel.addstr(string[5:-5] + "\n", curses.color_pair(LOG_YELLOW))
    elif string[2:4] == "94": #Log
        panel.addstr(string[5:-5] + "\n", curses.color_pair(LOG_CYAN))
    else: #debug
        panel.addstr(string, curses.color_pair(LOG))
    panel.refresh()

def kc_auto_kick_start(log_panel):
    # create a new thread
    kc_auto = threading.Thread(target=run_external_program,args=[log_panel])
    # Kill the child thread if parent is dead
    kc_auto.daemon = True 

    # start the thread
    kc_auto.start()
    return kc_auto


def run_external_program(panel):
    # Start the external program and redirect its output
    global process
    process = subprocess.Popen(['python3.7', 'kcauto', '--cli', '--cfg', 'config'], stdout=subprocess.PIPE)

    global pop_up_lock
    # Turn on scrolling for the log window
    # Read and write the output to the desired panel
    output = '' 
    while process.poll() is None:
        output = process.stdout.readline().decode()
        if pop_up_lock == False:
            print_log(panel, output)

    print_log(panel, "kcauto ended")

def save_screen():
    # Initialize the screen
    screen = curses.initscr()

    # Create a new window that covers the entire screen
    win = curses.newwin(curses.LINES, curses.COLS, 0, 0)

    # Copy the entire screen to the new window
    
    curses.copywin(screen, win, 0, 0, 0, 0, curses.LINES - 1, curses.COLS - 1, True)

    # Clean up and restore the terminal
    curses.endwin()

    return win

def restore_screen(win):
    # Create a new window that covers the entire screen
    new_win = curses.newwin(curses.LINES, curses.COLS, 0, 0)

    # Copy the contents of the saved window to the new window
    curses.copywin(win, new_win, 0, 0, 0, 0, curses.LINES - 1, curses.COLS - 1, True)

    # Refresh the screen
    curses.refresh()

    return new_win


def main():
    signal.signal(signal.SIGINT, signal_handler)
    curses.wrapper(draw_menu)

def signal_handler(signal_num, frame):
    #print("CTRL+C detected. Exiting gracefully...")
    curses.endwin()
    exit(0)


if __name__ == "__main__":
    main()    