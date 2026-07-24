import os
import time
import curses
import subprocess
import psutil
from sys import platform, exit

from cui.macro import *

WINDOW_MIN_HEIGHT = 8
WINDOW_MIN_WIDTH = 45

POP_UP_MAX_HEIGHT = 20

pop_up_lock = False
paused_lock = False

log_buffer = []

process = None
psutil_proc = None
is_running = False

import re


def get_center_str_location(window, string):

    height, width = window.getmaxyx()

    x_center = int((width // 2) - (len(string) // 2))
    y_center = int(height // 2)
    return x_center, y_center


def print_string(window, offset_x, offset_y, string):
    x, y = get_center_str_location(window, string)
    window.addstr(y + offset_y, x + offset_x, string)


def print_log(panel, string):

    if pop_up_lock:
        log_buffer.append(string)
        return

    # Define regular expression pattern for ANSI color codes
    ansi_color_pattern = re.compile(r"\x1b\[([0-9;]+)m")

    # Split the text into chunks separated by ANSI color codes
    chunks = ansi_color_pattern.split(string)

    # Print each chunk with the appropriate color
    color = curses.color_pair(LOG)
    for chunk in chunks:
        if chunk == "":
            continue
        elif chunk.isdigit():
            if chunk == "91":  # Error
                color = curses.color_pair(LOG_RED)
            elif chunk == "92":  # Status
                color = curses.color_pair(LOG_GREEN)
            elif chunk == "93":  # Warnning
                color = curses.color_pair(LOG_YELLOW)
            elif chunk == "94":  # Log
                color = curses.color_pair(LOG_CYAN)
            else:  # debug
                color = curses.color_pair(LOG)
        else:
            # Print the chunk with the current color
            panel.addstr(chunk, color)

    # Refresh the screen and wait for user input
    panel.refresh()


def run_external_program(panel):
    # Start the external program and redirect its output

    global process, psutil_proc, is_running

    if platform.startswith("linux"):
        filename = "kcauto_custom"
        python_cmd = "python3"
        exec_path = f"./bin/kcauto_custom/{filename}"
    elif platform in ["darwin", "win32"]:
        filename = "kcauto_custom.exe"
        python_cmd = "python"
        exec_path = f"./bin/kcauto_custom/{filename}"
    else:
        raise TypeError("Non-supported OS.")

    common_args = ["--cli", "--cfg", "config_cui"]

    if os.path.isfile(exec_path):
        cmd = [exec_path] + common_args
        msg = f"Starting from {filename}\n"
    else:
        cmd = [python_cmd, "kcauto"] + common_args
        msg = f"{filename} does not exist\nStart kcauto in Python instead\n"

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    psutil_proc = psutil.Process(process.pid)
    is_running = True

    time.sleep(1)
    print_log(panel, msg)

    global pop_up_lock
    # Read and write the output to the desired panel
    # Sentinel must be '' (str), not b'' (bytes), because stdout is in text mode
    for line in iter(process.stdout.readline, ""):
        output = line.strip()
        if output:
            print_log(panel, f"{output}\n")

            if "Press Enter to continue" in output:
                global paused_lock
                paused_lock = True

    process.stdout.close()
    process.wait()
    is_running = False

    # Final log after the process ends
    print_log(panel, "kcauto ended\n")


def pause_external_program(panel):

    global psutil_proc, is_running
    if psutil_proc and psutil_proc.is_running():
        psutil_proc.suspend()
        is_running = False
        print_log(panel, "kcauto paused\n")


def resume_external_program(panel):

    global psutil_proc, is_running
    if psutil_proc and psutil_proc.is_running():
        psutil_proc.resume()
        is_running = True
        print_log(panel, "kcauto resumed\n")


def signal_handler(signal=None, frame=None):
    exit(0)
