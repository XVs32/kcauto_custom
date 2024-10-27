import curses

import cui.util as util
from cui.macro import *

HOURS = -1
MINS = 1

item_list = ["END TIME", "SORTIE COUNT"]

def pop_up_menu(stdscr, panel, timestamp, sortie_max_count):

    cur_item = item_list[0]

    x_center, y_center = util.get_center_str_location(panel, "SCHEDULER")
    panel.addstr(0, x_center, "SCHEDULER", curses.color_pair(LOG))

    while 1:

        for i, item in enumerate(item_list):
            if cur_item == item:
                color = curses.color_pair(LOG_GREEN)
            else:
                color = curses.color_pair(LOG)

            x_center, y_center = util.get_center_str_location(panel, item)
            panel.addstr(y_center + i - 1, x_center, item, color)

        panel.refresh()

        # Wait for next input
        key = stdscr.getch()

        if key == curses.KEY_DOWN or key == ord('j'):
            cur_item = item_list[1]
        elif key == curses.KEY_UP or key == ord('k'):
            cur_item = item_list[0]
        elif key == KEY_ENTER:
            break

    panel.clear()
    panel.border()

    if cur_item== "END TIME":
        x_center, y_center = util.get_center_str_location(panel, "SHUT DOWN AT")
        panel.addstr(0, x_center, "SHUT DOWN AT", curses.color_pair(LOG))

        hrs_or_mins = HOURS
        hrs  = int(timestamp[0:2])
        mins = int(timestamp[2:4])
        while 1:
            x_center, y_center = util.get_center_str_location(panel, "HH:MM")
            time_str = str((hrs + 24 - 1) % 24).rjust(2,"0") + ":" + str((mins + 60 -1) % 60).rjust(2,"0")
            panel.addstr(y_center - 1, x_center, time_str, curses.color_pair(LOG))
            if hrs_or_mins == HOURS:
                panel.addstr(y_center + 0, x_center  , str(hrs % 24).rjust(2,"0"), curses.color_pair(LOG_GREEN_ACTIVE))
                panel.addstr(y_center + 0, x_center+2, ":", curses.color_pair(LOG_GREEN))
                panel.addstr(y_center + 0, x_center+3  , str(mins % 60).rjust(2,"0"), curses.color_pair(LOG_GREEN))
            elif hrs_or_mins == MINS:
                panel.addstr(y_center + 0, x_center  , str(hrs % 24).rjust(2,"0"), curses.color_pair(LOG_GREEN))
                panel.addstr(y_center + 0, x_center+2, ":", curses.color_pair(LOG_GREEN))
                panel.addstr(y_center + 0, x_center+3  , str(mins % 60).rjust(2,"0"), curses.color_pair(LOG_GREEN_ACTIVE))
            time_str = str((hrs + 1) % 24).rjust(2,"0") + ":" + str((mins + 1) % 60).rjust(2,"0")
            panel.addstr(y_center + 1, x_center, time_str, curses.color_pair(LOG))

            panel.refresh()

            # Wait for next input
            key = stdscr.getch()
            if key == curses.KEY_DOWN or key == ord('j'):
                if hrs_or_mins == HOURS:
                    hrs = (hrs + 1) % 24
                elif hrs_or_mins == MINS:
                    mins = (mins + 1) % 60
            elif key == curses.KEY_UP or key == ord('k'):
                if hrs_or_mins == HOURS:
                    hrs = (hrs + 24 - 1) % 24
                elif hrs_or_mins == MINS:
                    mins = (mins + 60 - 1) % 60
            elif key == curses.KEY_RIGHT or key == ord('l'):
                hrs_or_mins = MINS
            elif key == curses.KEY_LEFT  or key == ord('h'):
                hrs_or_mins = HOURS
            elif key == KEY_ENTER:
                timestamp = str(hrs).rjust(2,"0") + str(mins).rjust(2,"0")
                break

    elif cur_item == "SORTIE COUNT":
        x_center, y_center = util.get_center_str_location(panel, "SORTIE STOP AFTER")
        panel.addstr(0, x_center, "SORTIE STOP AFTER", curses.color_pair(LOG))

        while 1:
            x_center, y_center = util.get_center_str_location(panel, "XXX")
            if sortie_max_count == 0:
                panel.addstr(y_center - 1, x_center, str("   "), curses.color_pair(LOG))
                panel.addstr(y_center + 0, x_center, str(sortie_max_count + 0).rjust(3,"0"), curses.color_pair(LOG_GREEN))
                panel.addstr(y_center + 1, x_center, str(sortie_max_count + 1).rjust(3,"0"), curses.color_pair(LOG))
            if sortie_max_count == 999:
                panel.addstr(y_center - 1, x_center, str(sortie_max_count + 1).rjust(3,"0"), curses.color_pair(LOG))
                panel.addstr(y_center + 0, x_center, str(sortie_max_count + 0).rjust(3,"0"), curses.color_pair(LOG_GREEN))
                panel.addstr(y_center + 1, x_center, str("   "), curses.color_pair(LOG))
            elif sortie_max_count > 0 and sortie_max_count < 999:
                panel.addstr(y_center - 1, x_center, str(sortie_max_count - 1).rjust(3,"0"), curses.color_pair(LOG))
                panel.addstr(y_center + 0, x_center, str(sortie_max_count + 0).rjust(3,"0"), curses.color_pair(LOG_GREEN))
                panel.addstr(y_center + 1, x_center, str(sortie_max_count + 1).rjust(3,"0"), curses.color_pair(LOG))

            panel.refresh()

            # Wait for next input
            key = stdscr.getch()
            if key == curses.KEY_DOWN or key == ord('j'):
                if sortie_max_count < 999:
                    sortie_max_count += 1
            elif key == curses.KEY_UP or key == ord('k'):
                if sortie_max_count > 0:
                    sortie_max_count -= 1
            elif key == KEY_ENTER:
                break
             
    return timestamp, sortie_max_count

def get_end_time(config):
    for rule in config["scheduler.rules"]:
        if rule.split(":")[0] == "time" and rule.split(":")[2] == "stop" and rule.split(":")[3] == "kcauto":
            return rule.split(":")[1]
    return "disable"

def get_sortie_count(config):
    for rule in config["scheduler.rules"]:
        if rule.split(":")[0] == "sorties_run" and rule.split(":")[2] == "stop" and rule.split(":")[3] == "combat":
            return int(rule.split(":")[1])
    return 0

def set_config(config, end_time, sortie_count):
    for i, rule in enumerate(config["scheduler.rules"]):
        if rule.split(":")[0] == "sorties_run" and rule.split(":")[2] == "stop" and rule.split(":")[3] == "combat":
            config["scheduler.rules"][i] = "sorties_run:" + str(sortie_count) + ":stop:combat"
        elif rule.split(":")[0] == "time" and rule.split(":")[2] == "stop" and rule.split(":")[3] == "kcauto":
            config["scheduler.rules"][i] = "time:" + str(end_time) + ":stop:kcauto"

    return
