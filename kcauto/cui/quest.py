import curses

import cui.util as util
from cui.macro import *
from constants import CONTEXT_SORTIE, CONTEXT_EXPEDITION, CONTEXT_PVP, CONTEXT_FACTORY, CONTEXT_REPAIR

from fleet.noro6 import Noro6 

DAILY = 1
WEEKLY = 2
MONTHLY = 3
QUARTERLY = 4
YEARLY = 5

QUEST_LIST = {}
QUEST_LIST[CONTEXT_SORTIE] = {}
QUEST_LIST[CONTEXT_EXPEDITION] = {}
QUEST_LIST[CONTEXT_PVP] = {}
QUEST_LIST[CONTEXT_FACTORY] = {}
QUEST_LIST[CONTEXT_REPAIR] = {}

QUEST_LIST[CONTEXT_SORTIE][DAILY] = {}
QUEST_LIST[CONTEXT_SORTIE][WEEKLY] = {}
QUEST_LIST[CONTEXT_SORTIE][MONTHLY] = {}
QUEST_LIST[CONTEXT_SORTIE][QUARTERLY] = {}
QUEST_LIST[CONTEXT_SORTIE][YEARLY] = {}

QUEST_LIST[CONTEXT_PVP][DAILY] = {}
QUEST_LIST[CONTEXT_PVP][WEEKLY] = {}
QUEST_LIST[CONTEXT_PVP][MONTHLY] = {}
QUEST_LIST[CONTEXT_PVP][QUARTERLY] = {}
QUEST_LIST[CONTEXT_PVP][YEARLY] = {}

QUEST_LIST[CONTEXT_EXPEDITION][DAILY] = {}
QUEST_LIST[CONTEXT_EXPEDITION][WEEKLY] = {}
QUEST_LIST[CONTEXT_EXPEDITION][MONTHLY] = {}
QUEST_LIST[CONTEXT_EXPEDITION][QUARTERLY] = {}
QUEST_LIST[CONTEXT_EXPEDITION][YEARLY] = {}

QUEST_LIST[CONTEXT_REPAIR][DAILY] = {}
QUEST_LIST[CONTEXT_REPAIR][WEEKLY] = {}
QUEST_LIST[CONTEXT_REPAIR][MONTHLY] = {}
QUEST_LIST[CONTEXT_REPAIR][QUARTERLY] = {}
QUEST_LIST[CONTEXT_REPAIR][YEARLY] = {}

QUEST_LIST[CONTEXT_FACTORY][DAILY] = {}
QUEST_LIST[CONTEXT_FACTORY][WEEKLY] = {}
QUEST_LIST[CONTEXT_FACTORY][MONTHLY] = {}
QUEST_LIST[CONTEXT_FACTORY][QUARTERLY] = {}
QUEST_LIST[CONTEXT_FACTORY][YEARLY] = {}

MAX_QUEST_COL = 16

TAB_ORDER = [CONTEXT_SORTIE, CONTEXT_PVP, CONTEXT_EXPEDITION, CONTEXT_FACTORY, CONTEXT_REPAIR]
QUEST_ORDER = [DAILY, WEEKLY, MONTHLY, QUARTERLY, YEARLY]

BOARDER_WIDTH = 1
COL_NEEDED_WIDTH = 5

CURSER_X = 0
CURSER_Y = 1

quest_info = []

def pop_up_menu(stdscr, panel, config):
    
    global quest_info
    if quest_info == []:
        with open('data/quests/kc3_quests_en.json', 'r', encoding='utf-8') as f:
            import json
            quest_info = json.load(f)    
        
        with open('data/quests/quests.json', 'r', encoding='utf-8') as f:
            import json
            quest_list = json.load(f)    
            
        for quest_name in quest_list:
            context = None
            
            is_time_limit = False
            quest_name_ori = quest_name
            if quest_name[0:4].isdigit():
                is_time_limit = True
                quest_name=quest_name[4:]
            
            if quest_name[0] == 'B':
                context = CONTEXT_SORTIE
            elif quest_name[0] == 'C':
                context = CONTEXT_PVP
            elif quest_name[0] == 'D':
                context = CONTEXT_EXPEDITION
            elif quest_name[0] == 'E':
                context = CONTEXT_REPAIR
            elif quest_name[0] == 'F':
                context = CONTEXT_FACTORY
            else:
                continue
            
            quest_type = None
            if quest_name[1] == 'd':
                quest_type = DAILY
            elif quest_name[1] == 'w':
                quest_type = WEEKLY
            elif quest_name[1] == 'm':
                quest_type = MONTHLY
            elif quest_name[1] == 'q':
                quest_type = QUARTERLY
            elif quest_name[1] == 's':
                quest_type = QUARTERLY
            elif quest_name[1] == 'y':
                quest_type = YEARLY
            elif is_time_limit==True:
                quest_type = DAILY
            else:
                continue
                
            quest_id = None
            
            for id in quest_info:
                if quest_info[id]["code"] == quest_name_ori:
                    quest_id = id
                    break
                
            QUEST_LIST[context][quest_type][quest_name_ori] = [0, quest_id]
    
    current_tab = CONTEXT_SORTIE
    curser = [0, 0]
    
    height, width = panel.getmaxyx()
    
    col_width = (width - BOARDER_WIDTH*2) // 5
    
    left_pad = (col_width - COL_NEEDED_WIDTH) // 2
    
    col = [BOARDER_WIDTH +left_pad, 
             BOARDER_WIDTH + left_pad + col_width, 
             BOARDER_WIDTH + left_pad + col_width*2, 
             BOARDER_WIDTH + left_pad + col_width*3, 
     
             BOARDER_WIDTH + left_pad + col_width*4]
    
    tab_height = 1
    info_height = 2
    quest_height = min(height - (tab_height + info_height), MAX_QUEST_COL)
    
    row = [0, tab_height, tab_height + quest_height]
    
    #read current quest status from config
    for quest in config["quest.quests"]:
        
        is_time_limit = False
        quest_name_ori = quest
        if quest[0:4].isdigit():
            is_time_limit = True
            quest=quest[4:]
            
        if quest[0] == 'B':
            context = CONTEXT_SORTIE
        elif quest[0] == 'C':
            context = CONTEXT_PVP
        elif quest[0] == 'D':
            context = CONTEXT_EXPEDITION
        elif quest[0] == 'E':
            context = CONTEXT_REPAIR
        elif quest[0] == 'F':
            context = CONTEXT_FACTORY
        
        quest_type = None
        if quest[1] == 'd':
            quest_type = DAILY
        elif quest[1] == 'w':
            quest_type = WEEKLY
        elif quest[1] == 'm':
            quest_type = MONTHLY
        elif quest[1] == 'q':
            quest_type = QUARTERLY
        elif quest[1] == 's':
            quest_type = QUARTERLY
        elif quest[1] == 'y':
            quest_type = YEARLY
        elif is_time_limit == True:
            quest_type = DAILY
            
        if quest_name_ori in QUEST_LIST[context][quest_type]:
            QUEST_LIST[context][quest_type][quest_name_ori][0] = 1
            
    y_offset = 0
    
    while True:
        
        panel.clear()
        panel.border()
        panel.addstr(row[0], col[0], 
                    ("<" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_SORTIE else " ")+"COM"+(">" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_SORTIE else " "),
                    curses.color_pair(SORTIE + (COLOR_REVERT * (int(current_tab == CONTEXT_SORTIE)))))
        panel.addstr(row[0], col[1], 
                    ("<" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_PVP else " ")+"PVP"+(">" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_PVP else " "),
                    curses.color_pair(PVP + (COLOR_REVERT * (int(current_tab == CONTEXT_PVP)))))
        panel.addstr(row[0], col[2], 
                    ("<" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_EXPEDITION else " ")+"EXP"+(">" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_EXPEDITION else " "),
                    curses.color_pair(EXP + (COLOR_REVERT * (int(current_tab == CONTEXT_EXPEDITION)))))
        panel.addstr(row[0], col[3], 
                    ("<" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_FACTORY else " ")+"FAC"+(">" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_FACTORY else " "),
                    curses.color_pair(FACTORY + (COLOR_REVERT * (int(current_tab == CONTEXT_FACTORY)))))
        panel.addstr(row[0], col[4], 
                    ("<" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_REPAIR else " ")+"SUP"+(">" if curser[CURSER_Y] == 0 and current_tab == CONTEXT_REPAIR else " "),
                    curses.color_pair(REPAIR + (COLOR_REVERT * (int(current_tab == CONTEXT_REPAIR)))))
        
        for i, quest_type in enumerate(QUEST_ORDER):
            if curser[CURSER_Y] == i:
                color = curses.color_pair(LOG_GREEN)
            else:
                color = curses.color_pair(LOG)
                
            for j, quest in enumerate(QUEST_LIST[current_tab][quest_type]):
                
                quest_id = QUEST_LIST[current_tab][quest_type][quest][1]
                
                if j < (y_offset * -1):
                    continue
                
                if j > quest_height - y_offset - 1:
                    break
                
                if curser[CURSER_Y] - 1  == j and curser[CURSER_X] == i:
                    color = curses.color_pair(LOG_GREEN)
                    
                    panel.addstr(row[2], 1, quest_info[quest_id]["desc"][0:width-2], curses.color_pair(LOG))
                    if len(quest_info[quest_id]["desc"]) > width-2:
                        panel.addstr(row[2]+1, 1, quest_info[quest_id]["desc"][width-2:width*2-4], curses.color_pair(LOG))
                    if len(quest_info[quest_id]["desc"]) > (width-2)*2 and row[2]+2 < height:
                        panel.addstr(row[2]+2, 1, quest_info[quest_id]["desc"][(width-2)*2:(width-2)*3], curses.color_pair(LOG))
                    
                else:
                    color = curses.color_pair(LOG)
                panel.addstr(row[1] + j + y_offset, col[i], (" " if QUEST_LIST[current_tab][quest_type][quest][0] == 0 else "*") + quest.rjust(COL_NEEDED_WIDTH-1, ' '), color)
                
        
        
        
        panel.refresh()

        # Wait for next input
        key = stdscr.getch()
    
        if key == curses.KEY_DOWN or key == ord('j'):
            if curser[CURSER_Y] < len(QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]]]):
                curser[CURSER_Y] += 1
            elif curser[CURSER_Y] == 0:
                curser[CURSER_X] = 0
                curser[CURSER_Y] += 1
                
            y_offset = min(0, quest_height - curser[CURSER_Y])
            
        elif key == curses.KEY_UP or key == ord('k'):
            if curser[CURSER_Y] > 0:
                curser[CURSER_Y] -= 1
                if curser[CURSER_Y] == 0:
                    curser[CURSER_X] = TAB_ORDER.index(current_tab)
                else:
                    y_offset = max(y_offset, -(curser[CURSER_Y] - 1))
                    
        elif key == curses.KEY_RIGHT or key == ord('l'):
            if curser[CURSER_Y] == 0:
                if current_tab != TAB_ORDER[-1]:
                    current_tab = TAB_ORDER[TAB_ORDER.index(current_tab)+1]
                    curser[CURSER_X] = TAB_ORDER.index(current_tab)
            else:
                if QUEST_ORDER[curser[CURSER_X]] != YEARLY:
                    if len(QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]+1]]) == 0:
                        continue
                    if curser[CURSER_Y] > len(QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]+1]]):
                        curser[CURSER_Y] = len(QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]+1]])
                    curser[CURSER_X] += 1
        
        elif key == curses.KEY_LEFT or key == ord('h'):
            if curser[CURSER_Y] == 0:
                if current_tab != TAB_ORDER[0]:
                    current_tab = TAB_ORDER[TAB_ORDER.index(current_tab)-1]
                    curser[CURSER_X] = TAB_ORDER.index(current_tab)
            else:
                if QUEST_ORDER[curser[CURSER_X]] != DAILY:
                    if len(QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]-1]]) == 0:
                        continue
                    if curser[CURSER_Y] > len(QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]-1]]):
                        curser[CURSER_Y] = len(QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]-1]])
                    curser[CURSER_X] -= 1
                        
        elif key == KEY_ENTER:
            if curser[CURSER_Y] != 0:
                quest = list(QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]]].keys())[curser[CURSER_Y]-1]
                if QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]]][quest][0] == 0:
                    QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]]][quest][0] = 1
                else:
                    QUEST_LIST[current_tab][QUEST_ORDER[curser[CURSER_X]]][quest][0] = 0
                    
        elif key == ord('?') or key == KEY_ESC or key == ord('q'):
            break
    
    return None

def set_config(config):
    
    config["quest.enabled"] = False
    config["quest.quests"] = []
    
    for i, tab in enumerate(TAB_ORDER): 
        for j, quest_type in enumerate(QUEST_ORDER):
            for k, quest in enumerate(QUEST_LIST[tab][quest_type]):
                
                if QUEST_LIST[tab][quest_type][quest][0] == 1:
                    config["quest.enabled"] = True
                    config["quest.quests"].append(quest)
    
    return
