import sys,os
import signal
import curses
import json
import threading
import subprocess

EXP = 0
SORTIE = 1
SCHEDULER = 2
PVP = 3
LOG = 4

KEY_ENTER = 10

pop_up_lock = False

process = None

def draw_menu(stdscr):

    # open the file for reading
    with open('configs/config.json') as f:
        # parse the JSON data using json.load()
        data = json.load(f)
    f.close()

    k = 0
    curses.curs_set(0)

    # Clear and refresh the screen for a blank canvas
    stdscr.clear()
    stdscr.refresh()


    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)

    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_CYAN)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_GREEN)
    curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_WHITE)

    curses.init_pair(11, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(12, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(13, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(14, curses.COLOR_CYAN, curses.COLOR_BLACK)

    
    # Define the sub-panels
    top = 0
    left = 0
    next_top = 3 * curses.LINES // 7
    next_left = curses.COLS // 5
    expedition_panel = curses.newwin(next_top - top, next_left - left, top, left)
    top = next_top 
    left = 0
    next_top = 5 * curses.LINES // 7
    next_left = curses.COLS // 5
    sortie_panel = curses.newwin(next_top - top, next_left - left, top, left)
    top = next_top 
    left = 0 
    next_top = 6 * curses.LINES // 7
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

    

    # Define the panels list
    panels = [expedition_panel, sortie_panel, scheduler_panel, pvp_panel, log_panel]

    # Define the initial active panel
    active_panel = 0
    stdscr.clear()
    stdscr.refresh()

    kc_auto = kc_auto_kick_start(log_panel)

    # Loop where k is the last character pressed
    while (k != ord('q')):

        active_panel = get_next_active_panel(active_panel, k)

        # Draw the sub-panels
        for i, panel in enumerate(panels):
            if i == active_panel:
                panel.bkgd(curses.color_pair(i + 1 + 5))
            else:
                panel.bkgd(curses.color_pair(i + 1))

            if panel == expedition_panel:
                exp = [data["expedition.fleet_2"], data["expedition.fleet_3"], data["expedition.fleet_4"]]

                string = ','.join(map(str, exp[0]))
                print_string(panel, 0, -1, string)

                string = ','.join(map(str, exp[1]))
                print_string(panel, 0, 0, string)

                string = ','.join(map(str, exp[2]))
                print_string(panel, 0, 1, string)

            elif panel == sortie_panel:
                sortie_map = data["combat.sortie_map"]
                sortie_fleet = data["combat.fleet_presets"]

                print_string(panel, 0, 0, str(sortie_map))

                string = ','.join(map(str, sortie_fleet))
                print_string(panel, 0, 1, string)

            elif panel == pvp_panel:
                pvp_fleet = data["pvp.fleet_preset"]
                print_string(panel, 0, 0, str(pvp_fleet))

        for panel in panels:
            # Refresh the sub-panels
            panel.refresh()
        
        if k == KEY_ENTER:
            kc_auto, data = open_pop_up(kc_auto, stdscr, panels, active_panel, data)
            log_panel.redrawwin()
            k = 0
        else:
            # Wait for next input
            k = stdscr.getch()

        for panel in panels:
            if panel == log_panel:
                continue
            # Refresh the sub-panels
            panel.clear()
            panel.refresh()

def open_pop_up(thread, stdscr, panels, active_panel, data):

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
        # open the file for reading
        with open('data/expedition/expedition_preset.json') as f:
            # parse the JSON data using json.load()
            expedition_preset = json.load(f)
        f.close()

        active_preset_id=0
        while 1:
            for i, preset in enumerate(expedition_preset):
                if i == active_preset_id:
                    active_preset = preset
                    popup_win.addstr(i + 1, 1, preset, curses.color_pair(12))
                else:
                    popup_win.addstr(i + 1, 1, preset, curses.color_pair(5))

            popup_win.refresh()

            # Wait for next input
            key = stdscr.getch()

            if key == curses.KEY_DOWN or key == ord('j'):
                if active_preset_id < len(expedition_preset) - 1:
                    active_preset_id += 1
            elif key == curses.KEY_UP or key == ord('k'):
                if active_preset_id > 0:
                    active_preset_id -= 1
            elif key == KEY_ENTER:
                data["expedition.fleet_2"] = expedition_preset[active_preset][0]
                data["expedition.fleet_3"] = expedition_preset[active_preset][1]
                data["expedition.fleet_4"] = expedition_preset[active_preset][2]
                break

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
                panel.refresh()

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
                        json.dump(data, output, indent=4, sort_keys=True)
                    output.close()
                    
                    # send a SIGTERM signal to terminate the subprocess
                    process.send_signal(subprocess.signal.SIGTERM)
                    thread.join()

                    thread = kc_auto_kick_start(panels[4])
                break

    pop_up_lock = False
    return thread, data

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
        panel.addstr(string[5:-5] + "\n", curses.color_pair(11))
    elif string[2:4] == "92": #Status
        panel.addstr(string[5:-5] + "\n", curses.color_pair(12))
    elif string[2:4] == "93": #Warnning
        panel.addstr(string[5:-5] + "\n", curses.color_pair(13))
    elif string[2:4] == "94": #Log
        panel.addstr(string[5:-5] + "\n", curses.color_pair(14))
    else: #debug
        panel.addstr(string, curses.color_pair(5))
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