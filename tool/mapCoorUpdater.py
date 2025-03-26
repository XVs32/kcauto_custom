#! python3
import os 
import time
from pynput import mouse, keyboard
import string
import json

print('Press Ctrl-C to quit.')

fileSaved = False
upper_left_x = 0
upper_left_y = 0
click_count = 0

mapData = {}
nodeList = []
nodeType = {}

def init():
    
    global nodeType
    nodeType["boss"] = False
    nodeType["air"] = False
    nodeType["sub"] = False
    nodeType["select"] = False
    
    data = getKc3kaiEdges()
    kc3WorldId = getLastEventWorldId(data)
    
    #print out the list of files
    
    mapList = getMapList(data, kc3WorldId)
    for i, f in enumerate(mapList):
        print('\t', i+1, f'E-{f.split("-")[-1]}')
        
    mapId = input(f'Choose the event map(1~{i+1}):')
    
    getNodeList(data, f'World {kc3WorldId}-{mapId}')
        
    global mapData
    
    mapData["world"] = "E"
    mapData["subworld"] = int(mapId)
    
    mapData["enemy_context"] = set()
    
    mapData["enemy_context"].add("carriers")
    mapData["enemy_context"].add("transports")
    
    mapData["nodes"] = {}
    mapData["edges"] = data[f'World {kc3WorldId}-{mapId}']
    
    mapData["panel"] = int(input(f'Choose the panel this event map is on(1~9), use 1 if you are not sure:'))
    mapData["page"] = int(input(f'Choose the page this event map is on(1~9):'))
    
    print(f'Click upper left on map:')
    
    # Create listeners
    keyboard_listener = keyboard.Listener(on_press=on_press)
    mouse_listener = mouse.Listener(on_click=on_click)

    # Start both listeners in separate threads
    keyboard_listener.start()
    mouse_listener.start()

    # Keep the main thread running
    keyboard_listener.join()
    mouse_listener.join()


def getKc3kaiEdges():
    #read json file from kc3kai github
    import requests
    url = 'https://raw.githubusercontent.com/KC3Kai/KC3Kai/refs/heads/master/src/data/edges.json'
    response = requests.get(url)
    return response.json()
        
def getLastEventWorldId(data):
   #read all keys from the json file
    keys = data.keys()
    
    #all keys are in the format of "World 1-3", "World 60-3", etc.
    #split the key by "-", and get the first part of the key
    #then split the first part by " ", and get the second part of the key
    #the second part is the world id
    worldIds = set()
    for key in keys:
        worldIds.add(int(key.split("-")[0].split(" ")[1]))
    #get the max world id
    worldIds = list(worldIds)
    worldIds.sort()
    return str(worldIds[-1])

def getMapList(data, worldId):
    #return all keys that start with "World {worldId}-"
    return [key for key in data.keys() if key.startswith(f'World {worldId}-')]

def getNodeList(data, key):
    
    global nodeList
    print(key)
    nodeList = set()
    
    for edge in data[key]:
        nodeList.add(data[key][edge][0])
        nodeList.add(data[key][edge][1])
        
    #remove any values contains "start"
    nodeList = [node for node in nodeList if "Start" not in node]
    
    nodeList = list(nodeList)
    nodeList.sort()
    
    print(nodeList)
    return nodeList

def on_click(x, y, button, pressed):

    global upper_left_x
    global upper_left_y
    global click_count
    global nodeList

    if pressed == False:
        return

    if click_count == 0:
        upper_left_x = x
        upper_left_y = y
        positionStr = 'Upper left X: ' + str(x).rjust(4) + ' Y: ' + str(y).rjust(4)
        print(positionStr)
        print(f'Click next node {nodeList[click_count]} on the map:')
    else:
        
        print(f'Node {nodeList[click_count-1]}: [{str(x-upper_left_x).rjust(4)}, {str(y-upper_left_y).rjust(4)}]')
        
        global mapData
        mapData["nodes"][nodeList[click_count-1]]={}
        mapData["nodes"][nodeList[click_count-1]]["coords"] = [x-upper_left_x, y-upper_left_y]
        
        mapData["nodes"][nodeList[click_count-1]]["types"] = []
        if nodeType["boss"]:
            mapData["nodes"][nodeList[click_count-1]]["types"].append("boss")
            nodeType["boss"] = False
        if nodeType["air"]:
            mapData["nodes"][nodeList[click_count-1]]["types"].append("air")
            nodeType["air"] = False
        if nodeType["sub"]:
            mapData["nodes"][nodeList[click_count-1]]["types"].append("sub")
            mapData["enemy_context"].add("subs")
            nodeType["sub"] = False
        if nodeType["select"]:
            mapData["nodes"][nodeList[click_count-1]]["types"].append("select")
            nodeType["select"] = False
            
        if mapData["nodes"][nodeList[click_count-1]]["types"] == []:
            mapData["nodes"][nodeList[click_count-1]].pop('types', None)
        
        
        if click_count < len(nodeList):
            print(f'Click next node {nodeList[click_count]} on the map:')
        else:
            #save the data to a file
            mapData["enemy_context"] = list(mapData["enemy_context"])
            
            print(f'All nodes are clicked. Saving to file...')
            print(mapData)
            with open(f'../data/combat/E-{mapData["subworld"]}.json', 'w') as f:
                json.dump(mapData, f, indent=4)
            global fileSaved
            fileSaved = True

    click_count += 1
    
    return

#listen to keyboard interrupt
def on_press(key):
    global nodeType
    if key == keyboard.KeyCode.from_char('b'):
        nodeType["boss"] = not nodeType["boss"]
        if nodeType["boss"]:
            print("Next node is defined as the boss node")
        else:
            print("Boss node define is removed")
    elif key == keyboard.KeyCode.from_char('a'):
        nodeType["air"] = not nodeType["air"]
        if nodeType["air"]:
            print("Next node is defined as the air node")
        else:
            print("Air node define is removed")
    elif key == keyboard.KeyCode.from_char('s'):
        nodeType["sub"] = not nodeType["sub"]
        if nodeType["sub"]:
            print("Next node is defined as the sub node")
        else:
            print("Sub node define is removed")
    elif key == keyboard.KeyCode.from_char('o'):
        nodeType["select"] = not nodeType["select"]
        if nodeType["select"]:
            print("Next node is defined as the optional path node")
        else:
            print("Optional path node define is removed")

    return 

try:
    init()
    while(fileSaved == False):
        time.sleep(1)    
    keyboard.Listener.stop()
    mouse.Listener.stop()
except KeyboardInterrupt:
    print('\n')