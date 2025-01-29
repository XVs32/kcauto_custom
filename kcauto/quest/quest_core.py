import math
from datetime import datetime, timedelta
from sys import exit
from pyvisauto import Region
from random import randint

import api.api_core as api
import combat.combat_core as com
import config.config_core as cfg
import stats.stats_core as sts
import util.kca as kca_u
import expedition.expedition_core as exp
from constants import NEAR_EXACT, PAGE_NAV
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.expeditions import ExpeditionEnum
from kca_enums.maps import MapEnum
from quest.quest import Quest
from util.core_base import CoreBase
from util.json_data import JsonData
from util.kc_time import KCTime
from util.logger import Log


class QuestCore(CoreBase):
    QUEST_TYPE_WEIGHTS = {'daily': 1, 'weekly': 2, 'monthly': 3, 'other': 4}
    SORTIE = 1
    EXPEDITION = 2
    module_name = 'quest'
    module_display_name = 'Quest'
    quest_reset_time = datetime.now()
    max_quests = None
    quest_id_to_name = {}
    quest_library = {}
    quest_priority_library = []
    quest_to_sortie_maps = {}
    relevant_quests = []
    last_checked_context = 'reset'
    next_check_intervals = {}
    cur_page = None
    tot_page = None
    visible_quests = None
    

    def __init__(self):
        super().__init__()
        super().update_from_config()
        self._load_quest_data()
        self._load_quest_priority()

    def _load_quest_data(self):
        Log.log_msg("Loading Quest data.")
        quest_data = JsonData.load_json('data|quests|quests.json')
        for quest_name in quest_data:
            quest = Quest(quest_name, quest_data[quest_name])
            self.quest_library[quest_name] = quest
            self.quest_library[quest.quest_id] = quest
            self.quest_id_to_name[quest_data[quest_name]['id']] = quest_name
            self.quest_to_sortie_maps[quest_name] = quest_data[quest_name].get('recommended_map','')

    def _load_quest_priority(self):
        self.quest_priority_library = []

        Log.log_msg("Loading Quest priority data.")
        quest_priority = JsonData.load_json('data|quests|quest_priority.json')
        for quest_type in quest_priority:
            for quest in quest_priority[quest_type]:
                self.quest_priority_library.append(quest)

    def need_to_check(self, context):
        if datetime.now() > self.quest_reset_time:
            Log.log_msg("Quest check triggered by time.")
            self._reset_next_quest_reset_time()
            return True
        if self._get_quests_to_check_by_interval():
            Log.log_msg("Quest check triggered by interval.")
            return True
        if context is not None and context != self.last_checked_context:
            Log.log_msg("Quest check triggered by context change.")
            return True

    def update_quest_data(self, data):
        #self.cur_page = data.get('api_disp_page', 0)
        
        """Deleted by XVs32"""
        """self.tot_page = data.get('api_page_count', 0)"""
        self.visible_quests = data['api_list'] if data['api_list'] else []
        
        """Added by XVs32"""
        self.tot_page = math.ceil(len(self.visible_quests)/5)-1
        
        Log.log_debug(self.visible_quests_str)

    def manage_quests(self, context=None, fast_check=True):
        # dismiss Ooyodo
        kca_u.kca.r['center'].click()
        kca_u.kca.sleep(1)

        Log.log_msg(
            f"Manage {context} quests: ")

        if context and context != self.last_checked_context:
            fast_check = False
            self.last_checked_context = context
        if not context and self.last_checked_context:
            context = self.last_checked_context

        is_any_quest_turned_in = self._turn_in_quests(context)

        if fast_check == False or is_any_quest_turned_in == True:
            if context == "auto_sortie":
                self._auto_map_select(self.SORTIE)
            elif context == "auto_expedition":
                self._auto_map_select(self.EXPEDITION)
            else:
                self._toggle_quests(context)
        Log.log_msg(
            f"Tracked quests: {list(self.next_check_intervals.keys())}")

    @property
    def visible_quests_str(self):
        return_string = f"Visible quests: pg{self.cur_page}/{self.tot_page}"
        for q in self.visible_quests:
            if q == -1:
                break
            return_string += f", {q['api_no']} (state:{q['api_state']})"
        return return_string
    
    def _to_tab(self, tab_name):
        Log.log_msg(f"Navigating to {tab_name} quests tab.")
        if kca_u.kca.click_existing(
            'left', f'quest|filter_tab_{tab_name}.png') == True:
            kca_u.kca.wait(
                'left', f'quest|filter_tab_{tab_name}_active.png')
            api.api.update_from_api({KCSAPIEnum.QUEST_LIST}) #update visible_quests
        else:
            Log.log_error(f"Cannot find {tab_name} quests tab.")
            exit(1)

    def _turn_in_quests(self, context):
        Log.log_msg(
            f"Checking for quests to turn in and deactivate with {context} "
            "context.")
        quest_turned_in = False
        relevant_quests = self._get_quest_in_config([context, "expedition"])
        interval_check_quests = self._get_quests_to_check_by_interval()
        Log.log_msg(f"Relevant quests: {relevant_quests}")
        Log.log_debug(f"Quests to check: {interval_check_quests}")
        Log.log_msg("Navigating to active quests tab.")
        
        if kca_u.kca.click_existing('left', 'quest|filter_tab_active.png') == True:
            kca_u.kca.wait('left', 'quest|filter_tab_active_active.png')
            api.api.update_from_api({KCSAPIEnum.QUEST_LIST}) #update visible_quests
        else:
            kca_u.kca.click_existing(
                'lower', 'global|page_first.png', pad=PAGE_NAV)
            pass
        
        quest_offset = 0
        self.cur_page = 0
        
        while 1:
            for idx, quest in enumerate(self.visible_quests):
                
                quest_pos = idx - quest_offset

                if quest_pos < 0:
                    Log.log_error(f"Quest_pos is below 0, probably a bug around quest handling, send a bug report to dev if possible.")
                    break
                
                if quest == -1:
                    break

                if quest['api_no'] not in self.quest_library:
                    if quest['api_state'] == 3 and (self.cur_page+1)*5>quest_pos:
                        self._turn_in_quest_idx(quest_pos - self.cur_page*5)
                        quest_offset += 1
                        quest_turned_in = True
                    continue

                quest_i = self.quest_library[quest['api_no']]
                if quest['api_state'] == 2 and quest_i.name in relevant_quests:
                    Log.log_msg(f"Quest {quest_i.name} already active.")
                    if quest_i.name not in self.next_check_intervals:
                        # relevant quest active but not tracked; add to
                        # tracking with fresh intervals
                        self._track_quest(quest_i)
                    elif quest_i.name in interval_check_quests:
                        # quest is expected to be completed, but it isn't;
                        # re-track it with fresh intervals
                        self._track_quest(quest_i)

                """Edited by XVs32"""
                if quest['api_state'] == 3 and (self.cur_page+1)*5>quest_pos:
                    Log.log_msg(f"Turning in quest {quest_i.name}.")

                    """Edited by XVs32"""
                    self._turn_in_quest_idx(quest_pos - self.cur_page*5)
                    quest_offset += 1

                    self._untrack_quest(quest_i)
                    sts.stats.quest.quests_turned_in += 1
                    quest_turned_in = True
                    continue

                """Edited by XVs32"""
                if (quest['api_state'] == 2
                    and quest_i.name not in relevant_quests
                    and context is not None
                    and (self.cur_page+1)*5>quest_pos
                    and quest_i.name in cfg.config.quest.quests):
                    Log.log_msg(f"Deactivating quest {quest_i.name}.")

                    self._click_quest_idx(quest_pos - self.cur_page*5)
                    quest_offset += 1

                    self._untrack_quest(quest_i)
                    sts.stats.quest.quests_deactivated += 1
                    continue
                    
            if self.cur_page < self.tot_page:
                kca_u.kca.click_existing(
                    'lower_right', 'global|page_next.png', pad=PAGE_NAV)
                self.cur_page += 1
            else:
                break
            
        """Added by XVs32"""
        self.cur_page = 0
        return quest_turned_in
    
    
    def _find_next_quests(self, mode):
        """Method that finds the next sorties quest to work on

            Return:
                quest(str): The name of quest(ex. "Bd1")
        """
        
        if mode == self.SORTIE:
            self.relevant_quests = self._get_quest_in_config(["combat"]) #quest from config
        elif mode == self.EXPEDITION:
            self.relevant_quests = self._get_quest_in_config(["expedition"]) #quest from config
        
        for quest in self.quest_priority_library:
            if quest in self.relevant_quests:
                for visable_quest in self.visible_quests:
                    if visable_quest['api_state'] == 3: # This quest is done
                        continue
                    quest_id = self.quest_library[quest].quest_id
                    if quest_id == visable_quest['api_no']:
                        return quest
        return None
        


    def _toggle_quests(self, context):
        """Method that active quest to work on

            Args:
                context (str): The current focus/task of kcauto (combat,pvp,factory,reset).
        """
        Log.log_msg(
            f"Checking for quests to activate with {context} context.")
        # quests should only be activated at this point

        self.relevant_quests = self._get_quest_by_context(context)

        quest_types = sorted(
            list(self._get_types_from_quests(self.relevant_quests)),
            key=lambda quest_type: self.QUEST_TYPE_WEIGHTS[quest_type])
        
        remain_quest_slot = self.max_quests - len(self.visible_quests)

        for quest_type in quest_types:
            self._to_tab(quest_type)
            
            self.cur_page = 0
            count = 0
            while count < 100:
                Log.log_debug(f"count {count}")
                Log.log_debug(f"cur_page {self.cur_page}, tot_page {self.tot_page}.")
                for idx, quest in enumerate(self.visible_quests):
                    if quest == -1:
                        break

                    if quest['api_no'] not in self.quest_library:
                        continue

                    quest_i = self.quest_library[quest['api_no']]
                    Log.log_debug(f"Checking quset {quest['api_no']}:{quest_i.name}.")
                    
                    if (    (self.cur_page+1)*5 - idx > 0 
                        and (self.cur_page+1)*5 - idx < 6):
                        if quest_i in self.relevant_quests and quest['api_state'] == 1:
                            Log.log_msg(f"Activating quest {quest_i.name}.")
                            self._click_quest_idx(idx - self.cur_page*5)
                            self._track_quest(quest_i)
                            sts.stats.quest.quests_activated += 1
                            remain_quest_slot -= 1
                        elif (quest_i not in self.relevant_quests 
                              and quest['api_state'] == 2
                              and quest_i.name in cfg.config.quest.quests):
                            Log.log_msg(f"Deactivating quest {quest_i.name}.")
                            self._click_quest_idx(idx - self.cur_page*5)
                            self._untrack_quest(quest_i)
                            sts.stats.quest.quests_deactivated += 1
                            remain_quest_slot += 1
                
                if self.cur_page < self.tot_page :
                    kca_u.kca.click_existing(
                        'lower_right', 'global|page_next.png', pad=PAGE_NAV)
                    self.cur_page += 1
                elif remain_quest_slot <= 0:
                    return
                else:
                    break
                
                count += 1
            if count == 100:
                Log.log_error("Infinite loop detected, aborting.")
                exit(1)

    def _auto_map_select(self, mode):

        """
        Auto select sortie map mode
        expect in quest page currently
        """

        if kca_u.kca.click_existing(
            'left', f'quest|filter_tab_all.png') == True:
            kca_u.kca.wait(
                    'left', f'quest|filter_tab_all_active.png',
                    NEAR_EXACT)
            api.api.update_from_api({KCSAPIEnum.QUEST_LIST}) #update visible_quests
            Log.log_msg(f"api update done in auto map select.")

        if mode == self.SORTIE and cfg.config.combat.sortie_map_read_only == MapEnum.auto_map_selete:
            next_quest = self._find_next_quests(self.SORTIE)
            Log.log_debug(f"next_quest = {next_quest}")

            if next_quest != None:

                """Read quest progress""" 
                sortie_dict = kca_u.kca.get_quest_count(next_quest)

                sortie_list = []
                if sortie_dict == None:
                    Log.log_warn(f"Cannot get quest progress from kc3, use default in config file.")
                    sortie_list = self._get_sortie_map_from_quest(next_quest)
                    Log.log_debug(f"sortie_list = {sortie_list}")
                else:
                    for key in sortie_dict:
                        for i in range(0, sortie_dict[key]):
                            #sortie_list.append(key+"-"+next_quest)
                            sortie_list.append(next_quest +"-"+ key)

                com.combat.set_sortie_queue(sortie_list)

            Log.log_debug(f"_find_next_sorties_quests {self._find_next_quests(self.SORTIE)}.")
            Log.log_debug(f"get_sortie_queue {com.combat.get_sortie_queue()}.")
            
        elif mode == self.EXPEDITION:
            
            next_quest = self._find_next_quests(self.EXPEDITION)
            
            if next_quest != None:

                """Read quest progress""" 
                exp_dict = kca_u.kca.get_quest_count(next_quest)
                
                Log.log_debug(f'exp_dict {exp_dict}')
                
                if exp_dict == None:
                    Log.log_warn(f"Cannot get quest progress from kc3, kcauto_custom fail to select corresponding expedition")
                else:
                    
                    exp_list = []
                    for key in exp_dict:
                        if exp_dict[key] == 0:
                            continue
                        exp_list.append(ExpeditionEnum(exp.expedition.get_exp_enum_from_name(key)))
                    Log.log_debug(f'exp_list: {exp_list}')
                    
                    exp.expedition.cut_expedition_queue(exp_list)
                    
                    Log.log_debug(f'exp_rank: {exp.expedition.exp_rank}')

    def _get_sortie_map_from_quest(self, quest):
        Log.log_debug(f"self.quest_to_sortie_maps = {self.quest_to_sortie_maps}")
        return self.quest_to_sortie_maps[quest]

    def _get_quest_in_config(self,type_list):
        """Method that get all quests name which is available in game and enabled in config"""
        """type_list(str) : The type of quest to find(combat,pvp,factory,expedition)"""
        """Attention: Return quest name ONLY, no quest id is returned"""

        quest_groups = ['E']
        for type in type_list:
            if type == "combat" or type == "auto_sortie":
                quest_groups.append('B')
            elif type == "pvp":
                quest_groups.append('C')
            elif type == "factory":
                quest_groups.append('F')
            elif type == "expedition" or type == "auto_expedition":
                quest_groups.append('D')
            elif type != "reset":
                raise ValueError("Invalid quest type specified:" + type)
                

        quests_list = []
        for quest_name in cfg.config.quest.quests:
            if quest_name[0] not in quest_groups:
                continue
            quests_list.append(quest_name)
        
        return quests_list

    def _get_quest_by_context(self, context):
        relevant_quests = []
        if context == "combat" or type == "auto_sortie":
            quest_groups = ['B', 'E']
        elif context == 'pvp':
            quest_groups = ['C', 'E']
        elif context == 'factory':
            quest_groups = ['F', 'E']
        else:
            quest_groups = ['E']

        if cfg.config.expedition.enabled:
            quest_groups.append('D')

        for quest_name in cfg.config.quest.quests:
            if quest_name[0] not in quest_groups:
                continue
            q = self.quest_library[quest_name]

            if q.enemy_context:
                if not (
                        set(com.combat.map_data.enemy_context)
                        & set(q.enemy_context)):
                    continue
            if q.map_context:
                #The current combat map(ex. 3-5) without quest suffix(ex. 3-5-Bw4
                
                current_combat_map = MapEnum("B-" + cfg.config.combat.sortie_map.without_quest)
                if cfg.config.combat.sortie_map not in q.map_context and current_combat_map not in q.map_context:
                    continue
            if q.expedition_context:
                if not ( set([ExpeditionEnum(exp.expedition.cur_exp[1]),
                              ExpeditionEnum(exp.expedition.cur_exp[2]),
                              ExpeditionEnum(exp.expedition.cur_exp[3])])
                        & set(q.expedition_context)):
                    continue
            relevant_quests.append(q)

        return relevant_quests

    def _get_types_from_quests(self, quests):
        quest_types = set()
        for quest in quests:
            quest_types.add(quest.quest_type)
        return quest_types

    def _turn_in_quest_idx(self, idx):
        Log.log_msg(f"Turning in quest at position {idx}.")
        self._click_quest_idx(idx)
        kca_u.kca.wait('kc', 'quest|accept_reward_button.png', 30)
        while kca_u.kca.click_existing('kc', 'quest|accept_reward_button.png'):
            kca_u.kca.sleep(3)
        api.api.update_from_api({KCSAPIEnum.QUEST_LIST}) #update visible_quests

    def _click_quest_idx(self, idx):
        Log.log_msg(f"Clicking quest at position {idx}.")
        
        quest_list_region = Region(
            kca_u.kca.game_x + 230, kca_u.kca.game_y + 173 + (idx * 102),
            830, 30)
        quest_list_region.click()
        api.api.update_from_api(
            {KCSAPIEnum.QUEST_LIST, KCSAPIEnum.QUEST_TURN_IN}, need_all=False)
        kca_u.kca.sleep(1)

    def _untrack_quest(self, quest):
        Log.log_msg(f"No longer tracking quest {quest.name}.")
        self.next_check_intervals.pop(quest.name, None)

    def _track_quest(self, quest):
        Log.log_msg(f"Tracking quest {quest.name}.")
        self.next_check_intervals[quest.name] = self._generate_intervals(quest)

    def _generate_intervals(self, quest):
        next_combat = (
            quest.intervals[0] + sts.stats.combat.combat_sorties
            if quest.intervals[0] > 0
            else math.inf)
        next_pvp = (
            quest.intervals[1] + sts.stats.pvp.pvp_done
            if quest.intervals[1] > 0
            else math.inf)
        next_expedition = (
            quest.intervals[2] + sts.stats.expedition.expeditions_received
            if quest.intervals[2] > 0
            else math.inf)
        return (next_combat, next_pvp, next_expedition)

    def _get_quests_to_check_by_interval(self):
        quest_names = set()
        for quest_name in self.next_check_intervals:
            interval = self.next_check_intervals[quest_name]
            if (
                    sts.stats.combat.combat_sorties >= interval[0]
                    or sts.stats.pvp.pvp_done >= interval[1]
                    or sts.stats.expedition.expeditions_received >= interval[2]
            ):
                quest_names.add(quest_name)
        return quest_names

    @property
    def soonest_check_intervals(self):
        soonest_intervals = [math.inf, math.inf, math.inf]
        for quest_name in self.next_check_intervals:
            interval = self.next_check_intervals[quest_name]
            for idx in range(0, 3):
                if interval[idx] < soonest_intervals[idx]:
                    soonest_intervals[idx] = interval[idx]
        return soonest_intervals

    def _reset_next_quest_reset_time(self):
        jst_time = KCTime.convert_to_jst(datetime.now())
        if jst_time.hour == 5:
            temp_time = jst_time.replace(
                minute=randint(1, 5)) + timedelta(days=1)
        else:
            temp_time = jst_time.replace(hour=5, minute=randint(1, 5))
            if jst_time > temp_time:
                temp_time += timedelta(days=1)
        self.quest_reset_time = KCTime.convert_from_jst(temp_time)


quest = QuestCore()
