import curses
import subprocess

from cui.macro import *

pop_up_lock = False

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


def run_external_program(panel):
    # Start the external program and redirect its output
    global process
    process = subprocess.Popen(['python3.7', 'kcauto', '--cli', '--cfg', 'config_cui'], stdout=subprocess.PIPE)

    global pop_up_lock
    # Turn on scrolling for the log window
    # Read and write the output to the desired panel
    output = '' 
    while process.poll() is None:
        output = process.stdout.readline().decode()
        if pop_up_lock == False:
            print_log(panel, output)

    print_log(panel, "kcauto ended")

def signal_handler(signal_num, frame):
    #print("CTRL+C detected. Exiting gracefully...")
    curses.endwin()
    exit(0)