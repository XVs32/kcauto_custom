#! python3
import time
import click
from pynput import mouse
from pynput.mouse import Listener
import string

print('Press Ctrl-C to quit.')

first_click = True
upper_left_x = 0
upper_left_y = 0
click_count = 0

def init():
    with Listener(on_click=on_click) as listener:
        listener.join()

def on_click(x, y, button, pressed):

    global upper_left_x
    global upper_left_y
    global click_count

    if pressed == False:
        return

    if click_count == 0:
        upper_left_x = x
        upper_left_y = y
        positionStr = 'Upper left X: ' + str(x).rjust(4) + ' Y: ' + str(y).rjust(4)
        print(positionStr)
        print("\t\"" + string.ascii_uppercase[click_count] + "\": {")
    else:
        print("\t\t\"coords\": [" + str(x-upper_left_x).rjust(4) + ", " + str(y-upper_left_y).rjust(4) + "]")
        print("},")
        print("\t\"" + string.ascii_uppercase[click_count] + "\": {")

    click_count += 1
    return

try:
    init()
    while(1):
        time.sleep(1)    
except KeyboardInterrupt:
    print('\n')