import sys,os
import curses
import json

def draw_menu(stdscr):

    # open the file for reading
    with open('config.json') as f:
        # parse the JSON data using json.load()
        data = json.load(f)

    k = 0
    cursor_x = 0
    cursor_y = 0
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
    

    # Define the panels list
    panels = [expedition_panel, sortie_panel, scheduler_panel, pvp_panel, log_panel]

    # Define the initial active panel
    active_panel = 0
    stdscr.clear()
    stdscr.refresh()

    # Loop where k is the last character pressed
    while (k != ord('q')):

        if k == curses.KEY_DOWN or k == ord('j'):
            active_panel += 1
        elif k == curses.KEY_UP or k == ord('k'):
            active_panel += 1
        elif k == curses.KEY_RIGHT or k == ord('l'):
            active_panel += 1
        elif k == curses.KEY_LEFT or k == ord('h'):
            active_panel -= 1

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
        
        # Wait for next input
        k = stdscr.getch()

        for panel in panels:
            # Refresh the sub-panels
            panel.clear()
            panel.refresh()

def get_center_str_location(window, string):

    height, width = window.getmaxyx()

    x_center = int((width // 2) - (len(string) // 2) - len(string) % 2)
    y_center = int( height// 2 )
    return x_center, y_center

def print_string(window, offset_x, offset_y, string):
    x, y = get_center_str_location(window, string)
    window.addstr(y + offset_y, x + offset_x, string)

def main():
    curses.wrapper(draw_menu)

if __name__ == "__main__":
    main()