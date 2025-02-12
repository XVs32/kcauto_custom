import os
import time
import curses
import subprocess
from sys import platform, exit

from cui.macro import *

pop_up_lock = False
process = None

import re

def get_center_str_location(window, string):

    height, width = window.getmaxyx()

    x_center = int((width // 2) - (len(string) // 2))
    y_center = int( height// 2 )
    return x_center, y_center

def print_string(window, offset_x, offset_y, string):
    x, y = get_center_str_location(window, string)
    window.addstr(y + offset_y, x + offset_x, string)

def print_log(panel, string):

    # Define regular expression pattern for ANSI color codes
    ansi_color_pattern = re.compile(r'\x1b\[([0-9;]+)m')

    # Split the text into chunks separated by ANSI color codes
    chunks = ansi_color_pattern.split(string)

    # Print each chunk with the appropriate color
    color = curses.color_pair(LOG)
    for chunk in chunks:
        if chunk == '':
            continue
        elif chunk.isdigit():
            if chunk == "91": #Error
                color = curses.color_pair(LOG_RED)
            elif chunk == "92": #Status
                color = curses.color_pair(LOG_GREEN)
            elif chunk == "93": #Warnning
                color = curses.color_pair(LOG_YELLOW)
            elif chunk == "94": #Log
                color = curses.color_pair(LOG_CYAN)
            else: #debug
                color = curses.color_pair(LOG)
        else:
            # Print the chunk with the current color
            panel.addstr(chunk, color)

    # Refresh the screen and wait for user input
    panel.refresh()

def run_external_program(panel):
    # Start the external program and redirect its output
    global process
    
    if platform == "linux" or platform == "linux2":
        filename = "kcauto.bin"
        if os.path.isfile(filename):
            process = subprocess.Popen(
                ['./kcauto.bin', '--cli', '--cfg', 'config_cui'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,  # Enable text mode
                encoding='utf-8'  # Ensure UTF-8 decoding
            )
            time.sleep(1)
            print_log(panel, f"Starting from {filename}\n")
        else:
            process = subprocess.Popen(
                ['python3.7', 'kcauto', '--cli', '--cfg', 'config_cui'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,  # Enable text mode
                encoding='utf-8'  # Ensure UTF-8 decoding
            )
            time.sleep(1)
            print_log(panel, f"{filename} does not exist\n")
            print_log(panel, "Start kcauto in Python instead\n")
            
    elif platform == "darwin" or platform == "win32": 
        filename = "kcauto.exe"
        if os.path.isfile(filename):
            process = subprocess.Popen(
                ['kcauto.exe', '--cli', '--cfg', 'config_cui'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,  # Enable text mode
                encoding='utf-8'  # Ensure UTF-8 decoding
            )
            time.sleep(1)
            print_log(panel, f"Starting from {filename}\n")
        else:
            process = subprocess.Popen(
                ['python', 'kcauto', '--cli', '--cfg', 'config_cui'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,  # Enable text mode
                encoding='utf-8'  # Ensure UTF-8 decoding
            )
            time.sleep(1)
            print_log(panel, f"{filename} does not exist\n")
            print_log(panel, "Start kcauto in Python instead\n")
    else:
        raise TypeError("Non-supported OS.")
    
    global pop_up_lock
    # Read and write the output to the desired panel
    while process.poll() is None:
        output = process.stdout.readline().strip()  # Read line and remove extra whitespace
        if output:  # Only process non-empty lines
            print_log(panel, f"{output}\n")

    # Final log after the process ends
    print_log(panel, "kcauto ended\n")

def signal_handler(signal = None, frame = None):
    exit(0)