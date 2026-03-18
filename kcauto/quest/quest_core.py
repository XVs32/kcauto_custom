import math
from datetime import datetime, timedelta
from sys import exit
from util.pyvisauto import Region
from random import randint

import api.api_core as api
import combat.combat_core as com
import config.config_core as cfg
import fleet.fleet_core as flt
import pvp.pvp_core as pvp
import stats.stats_core as sts
import util.kca as kca_u
import expedition.expedition_core as exp
import nav.nav as nav
from constants import NEAR_EXACT, PAGE_NAV
from constants import CONTEXT_EXPEDITION, CONTEXT_PVP, CONTEXT_SORTIE, CONTEXT_FACTORY
from constants import CONTEXT_AUTO_EXPEDITION, CONTEXT_AUTO_SORTIE, CONTEXT_AUTO_PVP
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.quest_state import QuestStateEnum
from kca_enums.ship_types import ShipTypeEnum
from kca_enums.ship_class import ShipClassEnum 
from kca_enums.sorite_rank import SortieRankEnum
from kca_enums.maps import MapEnum
from quest.quest import Quest
from fleet.fleet import Fleet
from util.core_base import CoreBase
from util.json_data import JsonData
from util.kc_time import KCTime
from util.logger import Log


class QuestCore(CoreBase):
    
    CONTEXT_LOOKUP = {
        CONTEXT_AUTO_EXPEDITION: "auto_expedition",
        CONTEXT_AUTO_SORTIE: "auto_sortie",
        CONTEXT_AUTO_PVP: "auto_pvp",
        CONTEXT_SORTIE: "sortie",
        CONTEXT_EXPEDITION: "expedition",
        CONTEXT_PVP: "pvp",
        CONTEXT_FACTORY: "factory",
    }   
    
    ID = "id"
    CTYPE = "ctype"
    STYPE = "stype"
    ALLOWED_SHIP_TYPES = "allowed_ship_types"
    POSITION = "position"
    AMOUNT = "amount"
    COUNT_RULE = "count_rule"
    AT_LEAST = "at_least"
    AT_MOST = "at_most"
    EXACT = "exact"
    QUEST_TYPE_WEIGHTS = {'daily': 1, 'weekly': 2, 'monthly': 3, 'other': 4}
    module_name = 'quest'
    module_display_name = 'Quest'
    quest_reset_time = datetime.now()
    max_quests = None
    quest_priority_library : dict[int , list[Quest]] = {}
    is_quest_dom_cache_dirty = True
    _quest_dom_cache = None
    _context_cache = None
    _relevant_quests = []
    last_checked_context = None
    next_check_intervals : dict[int, Quest] = {}
    cur_page = None
    tot_page = None
    current_quest_list : list[Quest] = []
    active_quest_list : list[Quest] = []
    
    auto_select_quest : dict[int, Quest] = {
        CONTEXT_SORTIE: None,
        CONTEXT_PVP: None,
        CONTEXT_EXPEDITION: None,
        CONTEXT_FACTORY: None
    }

    def __init__(self):
        super().__init__()
        super().update_from_config()
        #self._load_quest_data()
        self._load_quest_priority()

    def _load_quest_priority(self):
        self.quest_priority_library = {}
        self.quest_priority_library[CONTEXT_SORTIE] = []
        self.quest_priority_library[CONTEXT_EXPEDITION] = []
        self.quest_priority_library[CONTEXT_PVP] = []
        self.quest_priority_library[CONTEXT_FACTORY] = []

        Log.log_msg("Loading Quest priority data.")
        quest_priority = JsonData.load_json('data|quests|sorite_quest_priority.json')
        for quest_type in quest_priority:
            for quest_name in quest_priority[quest_type]:
                self.quest_priority_library[CONTEXT_SORTIE].append(Quest(quest_name))
                
        quest_priority = JsonData.load_json('data|quests|expedition_quest_priority.json')
        for quest_type in quest_priority:
            for quest_name in quest_priority[quest_type]:
                self.quest_priority_library[CONTEXT_EXPEDITION].append(Quest(quest_name))
                
        quest_priority = JsonData.load_json('data|quests|pvp_quest_priority.json')
        for quest_type in quest_priority:
            for quest_name in quest_priority[quest_type]:
                self.quest_priority_library[CONTEXT_PVP].append(Quest(quest_name))

    def need_to_check(self, context):
        if datetime.now() > self.quest_reset_time:
            Log.log_msg("Quest check triggered by time.")
            self._reset_next_quest_reset_time()
            return True
        if self._get_quests_to_check_by_interval():
            Log.log_msg("Quest check triggered by interval.")
            return True
        if context != None and context != self.last_checked_context:
            Log.log_msg("Quest check triggered by context change.")
            return True

    def update_quest_data(self, data):
        
        self.current_quest_list = []
        self.active_quest_list = []
        if data is None or 'api_list' not in data:
            Log.log_error("Quest data is None or does not contain 'api_list'.")
            return
        if data["api_list"] is None:
            data["api_list"] = []
        for raw_quest_api in data['api_list']:
            if raw_quest_api == -1:
                continue
            self.current_quest_list.append(Quest(
                api_data=raw_quest_api))

            if self.current_quest_list[-1].state == QuestStateEnum.IN_PROGRESS:
                self.active_quest_list.append(self.current_quest_list[-1])
        
        self.tot_page = math.ceil(len(self.current_quest_list)/5)
        
        Log.log_debug_1(self.quests_str)

    def manage_quests(self, context=None, fast_check=True):
        # dismiss Ooyodo
        kca_u.kca.r['center'].click()
        kca_u.kca.sleep(1)

        Log.log_msg(
            f"Manage {self.CONTEXT_LOOKUP[context]} quests: ")

        if context != None and context != self.last_checked_context:
            fast_check = False
            self.last_checked_context = context
        if context == None and self.last_checked_context:
            context = self.last_checked_context
            
        is_any_quest_turned_in = self._turn_in_quests(context)
        if fast_check == False or is_any_quest_turned_in == True:
            if context != CONTEXT_AUTO_SORTIE and context != CONTEXT_AUTO_EXPEDITION and context != CONTEXT_AUTO_PVP:
                self._toggle_quests(context)
            else:
                self._auto_target_select(context)
                
        Log.log_msg(
            f"Tracked quests: {[self.next_check_intervals[quest_id].name for quest_id in self.next_check_intervals]}")

    @property
    def quests_str(self):
        return_string = f"Visible quests: pg{self.tot_page}"
        for q in self.current_quest_list:
            return_string += f", {q.quest_id}:{q.name}:{q.state.name})"
        return return_string
    
    def _to_tab(self, tab_name):
        Log.log_msg(f"Navigating to {tab_name} quests tab.")
        if kca_u.kca.click_existing(
            'left', f'quest|filter_tab_{tab_name}.png', similarity=NEAR_EXACT) == True:
            kca_u.kca.wait(
                'left', f'quest|filter_tab_{tab_name}_active.png', similarity=NEAR_EXACT)
            api.api.update_from_api({KCSAPIEnum.QUEST_LIST}) #update quest_list
        else:
            Log.log_error(f"Cannot find {tab_name} quests tab.")
            exit(1)

    def _turn_in_quests(self, context):
        Log.log_msg(
            f"Checking for quests to turn in and deactivate with {self.CONTEXT_LOOKUP[context]} "
            "context.")
        quest_turned_in = False
        Log.log_msg("Navigating to active quests tab.")
        
        if kca_u.kca.click_existing('left', 'quest|filter_tab_active.png', similarity=NEAR_EXACT) == True:
            kca_u.kca.wait('left', 'quest|filter_tab_active_active.png', similarity=NEAR_EXACT)
            api.api.update_from_api({KCSAPIEnum.QUEST_LIST}) #update quest_list
            
        kca_u.kca.click_existing(
            'lower', 'global|page_last.png', pad=PAGE_NAV) #start from last page
        
        self.cur_page = self.tot_page
        
        i = len(self.current_quest_list)-1
        
        while i >= 0:
            quest = self.current_quest_list[i]
            
            if not (quest.name in cfg.config.quest.quests):
                Log.log_debug_1(f"Quest {quest.quest_id}/{quest.name} is not in config.")
                if quest.state == QuestStateEnum.DONE:
                    self._turn_in_quest_idx(i)
                    quest_turned_in = True
            elif quest.state == QuestStateEnum.IN_PROGRESS and context != CONTEXT_AUTO_SORTIE and context != CONTEXT_AUTO_EXPEDITION and context != CONTEXT_AUTO_PVP:
                
                Log.log_msg(f"Checking if quest {quest.name} is relevant to {self.CONTEXT_LOOKUP[context]}.")
                
                deactivate_needed = False 
                if not self._is_relevent_quest(quest, context=context):
                    
                    deactivate_needed = True
                    if context != CONTEXT_EXPEDITION and self._is_relevent_quest(quest, context=CONTEXT_EXPEDITION):
                        deactivate_needed = False
                    
                if deactivate_needed == True:    
                    Log.log_msg(f"Deactivating quest {quest.name}.")
                    self._click_quest_idx(i)
                    self._untrack_quest(quest)
                    sts.stats.quest.quests_deactivated += 1
                elif deactivate_needed == False:
                    Log.log_msg(f"Quest {quest.name} already active.")
                    if self._quest_should_be_done(quest):
                        # quest is expected to be completed, but it isn't;
                        # re-track it with fresh intervals
                        self._track_quest(quest)
                    elif quest.quest_id not in self.next_check_intervals:
                        # relevant quest active but not tracked; add to
                        # tracking with fresh intervals
                        self._track_quest(quest)

            elif quest.state == QuestStateEnum.DONE:
                Log.log_msg(f"Turning in quest {quest.name}.")

                """Edited by XVs32"""
                self._turn_in_quest_idx(i)

                self._untrack_quest(quest)
                sts.stats.quest.quests_turned_in += 1
                quest_turned_in = True
            
            i-=1
               
        return quest_turned_in
    
    def _get_quests_rank_list(self, mode) -> list[Quest]:
        """Method that finds the next sorties quest to work on

            Return:
                quest(str): The name of quest(ex. "Bd1")
        """
        
        #@todo quest rank list is a static list, sperate combat and expedition quests into two files
        # that way _is_relevent_quest is not needed here anymore
        # that way _is_relevent_quest can assume Quest input always has api data in it
        
        ret = []
        
        for quest in self.quest_priority_library[mode]:
                
            if not (quest.name in cfg.config.quest.quests):
                Log.log_debug_1(f"Quest {quest.name} is not in config.")
                continue
            
            for current_quest in self.current_quest_list:
                if current_quest.quest_id != quest.quest_id or current_quest.state == QuestStateEnum.DONE:
                    continue
                
                ret.append(current_quest)
                
        return ret
 
    def _toggle_quests(self, context):
        """Method that active quest to work on

            Args:
                context (int): The current focus/task of kcauto (CONTEXT_SORTIE, CONTEXT_EXPETITION, CONTEXT_PVP, etc.).
        """
        Log.log_msg(
            f"Checking for quests to activate with {self.CONTEXT_LOOKUP[context]} context.")
        # quests should only be activated at this point
        if kca_u.kca.click_existing('left', 'quest|filter_tab_all.png', similarity=NEAR_EXACT) == True:
            kca_u.kca.wait('left', 'quest|filter_tab_all_active.png', similarity=NEAR_EXACT)
            api.api.update_from_api({KCSAPIEnum.QUEST_LIST}) #update quest_list
        
        remain_quest_slot = self.max_quests - len(self.active_quest_list)
        
        self.cur_page = 1
        
        check_order = list(range(len(self.current_quest_list)))
        
        for quest_priority in reversed(self.quest_priority_library[context]): 
            for i, current_quest in enumerate(self.current_quest_list):
                if current_quest.quest_id == quest_priority.quest_id:
                    check_order[i] = -1 
                    check_order.append(i)
                    break
        check_order.reverse()

        for i in check_order:
            
            if i == -1:
                continue
            
            quest = self.current_quest_list[i]
            
            if quest.state == QuestStateEnum.DONE:
                Log.log_warn(f"Quest {quest.name} is done, but not turned in.")
                continue
            elif quest.state == QuestStateEnum.IN_PROGRESS:
                # quest is in progress, check if it should be tracked
                continue
            else:
                
                if self._is_relevent_quest(quest, context=context):
                    Log.log_msg(f"Activating quest {quest.name}.")
                    self._click_quest_idx(i)
                    self._track_quest(quest)
                    remain_quest_slot -= 1
                    if remain_quest_slot <= 0:
                        Log.log_msg("Reached maximum quest slots, stopping activation.")
                        return
                
    def _auto_target_select(self, mode):

        """
        Auto select sortie map mode
        expect in quest page currently
        """

        if kca_u.kca.click_existing(
            'left', f'quest|filter_tab_all.png', similarity=NEAR_EXACT) == True:
            kca_u.kca.wait(
                    'left', f'quest|filter_tab_all_active.png',
                    NEAR_EXACT)
            api.api.update_from_api({KCSAPIEnum.QUEST_LIST}) #update quest_list
            Log.log_msg(f"API update done in #{self.CONTEXT_LOOKUP[mode]} auto map select.")

        if mode == CONTEXT_AUTO_SORTIE and cfg.config.combat.sortie_map_read_only == MapEnum.auto_map_select:
            next_quest = self._get_quests_rank_list(CONTEXT_SORTIE)
            if next_quest != []:
                next_quest = next_quest[0]
            else:
                Log.log_error(f"No sortie quests available, cannot auto select sortie map.")
                com.combat.enabled = False
                return
            
            self.auto_select_quest[CONTEXT_SORTIE] = next_quest    
            
            Log.log_success(f"Attempting to finish sortie quest {next_quest.name}.")

            """Read quest progress""" 
            sortie_dict = kca_u.kca.get_quest_count(target_quest=next_quest)

            sortie_list = []
            if sortie_dict == None:
                Log.log_warn(f"Cannot get quest progress from kc3, use default in config file.")
                sortie_list = list(MapEnum(map_name) for map_name in next_quest.recommended_map)
                Log.log_debug_1(f"sortie_list = {sortie_list}")
            else:
                for map_enum in sortie_dict:
                    for i in range(0, sortie_dict[map_enum]):
                        generated_map_name = f"{next_quest.name}-{map_enum.world_and_map_and_node}"
                        sortie_list.append(MapEnum(generated_map_name))
            
            com.combat.set_sortie_queue(sortie_list)

            Log.log_debug_1(f"get_sortie_queue {com.combat.get_sortie_queue()}.")
            
        elif mode == CONTEXT_AUTO_PVP:
            
            next_quest = self._get_quests_rank_list(CONTEXT_PVP)
            
            if next_quest != []:
                pvp.pvp.next_pvp_quest = next_quest[0]
                Log.log_success(f"Attempting to finish PvP quest {pvp.pvp.next_pvp_quest.name}.")
            else:
                pvp.pvp.next_pvp_quest = Quest(quest_id=303) #mork the next quest as Cd1, so kcauto use default PvP preset
                Log.log_success(f"No PvP quests available.")
                
            self.auto_select_quest[CONTEXT_PVP] = pvp.pvp.next_pvp_quest
            
        elif mode == CONTEXT_AUTO_EXPEDITION:
            
            quest_list = self._get_quests_rank_list(CONTEXT_EXPEDITION)
            
            for next_quest in reversed(quest_list):
                Log.log_success(f"Attempting to finish expedition quest {next_quest.name}.")
                """Read quest progress""" 
                exp_dict = kca_u.kca.get_quest_count(target_quest= next_quest)
                
                Log.log_debug_1(f'exp_dict {exp_dict}')
                
                if exp_dict == None:
                    Log.log_debug_1(f"Cannot get quest progress from kc3, use default in config file.")
                    exp_list = list(next_quest.exp_context)
                    if exp_list == []:
                        Log.log_debug_1(f"Cannot get quest info from kc3 and default config file; kcauto_custom failed to select corresponding expedition.")
                    else:
                        exp.expedition.cut_expedition_queue(exp_list)
                else:
                    exp_list = []
                    for map_enum in exp_dict:
                        if exp_dict[map_enum] > 0:
                            exp_list.append(map_enum)
                    Log.log_debug_1(f'exp_list: {exp_list}')
                    exp.expedition.cut_expedition_queue(exp_list)
                
                Log.log_debug_1(f'exp_rank: {exp.expedition.exp_rank}')

    def _turn_in_quest_idx(self, idx):
        """Method to turn in quest by index in the current quest list.
        
        Args:
            idx (int): The index of the quest in the current quest list. id starts from 0
        """
        Log.log_msg(f"Turning in quest at position {idx}.")
        
        self._click_quest_idx(idx)
        kca_u.kca.wait('kc', 'quest|accept_reward_button.png', 30)
        while kca_u.kca.click_existing('kc', 'quest|accept_reward_button.png'):
            kca_u.kca.sleep(3)
        api.api.update_from_api({KCSAPIEnum.QUEST_LIST}) #update quest_list

    def _click_quest_idx(self, idx):
        """Method to click on a quest by index in the current quest list.
        Args:
            idx (int): The index of the quest in the current quest list. id starts from 0
        """
        
        Log.log_debug_1(f"Clicking quest at position {idx}.")
        Log.log_msg(f"Moving from page {self.cur_page}/{self.tot_page} to {math.ceil((idx+1)/5)}/{self.tot_page}.")
        
        nav.navigate_list.to_page(self.tot_page, self.cur_page, math.ceil((idx+1)/5),nav.navigate_list.OP_MODE_QUEST)
        self.cur_page = math.ceil((idx+1)/5)
        
        quest_list_region = Region(
            kca_u.kca.game_x + 230, kca_u.kca.game_y + 173 + ((idx % 5) * 102),
            830, 30)
        quest_list_region.click()
        api.api.update_from_api(
            {KCSAPIEnum.QUEST_LIST, KCSAPIEnum.QUEST_TURN_IN}, process_all=False)
        kca_u.kca.sleep(1)

    def _untrack_quest(self, quest:Quest):
        Log.log_msg(f"No longer tracking quest {quest.name}.")
        self.next_check_intervals.pop(quest.quest_id, None)

    def _track_quest(self, quest : Quest):
        Log.log_msg(f"Tracking quest {quest.name}.")
        
        self.next_check_intervals[quest.quest_id] = quest
        self.next_check_intervals[quest.quest_id].next_intervals = self._generate_intervals(quest)
        
        return
    
    def meets_min_sortie_rank(self, current_context, last_sortie_result: SortieRankEnum = None) -> bool:
        """Return True if sortie_rank (or last_sortie_result) meets quest.min_sortie_rank."""
        
        if current_context == CONTEXT_PVP:
            pass
        elif current_context == CONTEXT_SORTIE:
            return last_sortie_result.is_at_least(
                self.auto_select_quest[CONTEXT_SORTIE].rank_requirement.get(
                    com.combat.get_sortie_queue()[0].without_quest_enum, 
                    SortieRankEnum.E))
            self.auto_select_quest[CONTEXT_PVP] = pvp.pvp.next_pvp_quest

    def _generate_intervals(self, quest :Quest):
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
        for quest_id in self.next_check_intervals:
            interval = self.next_check_intervals[quest_id].next_intervals
            if (
                    sts.stats.combat.combat_sorties >= interval[0]
                    or sts.stats.pvp.pvp_done >= interval[1]
                    or sts.stats.expedition.expeditions_received >= interval[2]
            ):
                quest_names.add(quest_id)
        return quest_names
    
    def _quest_should_be_done(self, quest : Quest):
        """Check if a quest needs to be checked based on its intervals."""
        
        if quest.quest_id not in self.next_check_intervals:
            return False
        
        interval = self.next_check_intervals[quest.quest_id].next_intervals
        return (
            sts.stats.combat.combat_sorties >= interval[0]
            or sts.stats.pvp.pvp_done >= interval[1]
            or sts.stats.expedition.expeditions_received >= interval[2]
        )

    @property
    def soonest_check_intervals(self):
        soonest_intervals = [math.inf, math.inf, math.inf]
        for quest_name in self.next_check_intervals:
            interval = self.next_check_intervals[quest_name].next_intervals
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

    def _is_relevent_quest(self, quest : Quest, context):
        """method to check if a quest is relevant to the current context.
        Args:
            quest (Quest): The quest to check.
            context_list (list): List of contexts to check against.
        Returns: 
            bool: True if the quest is relevant, False otherwise.
        """
        
        if quest is None or not isinstance(quest, Quest) or quest.quest_id is None:
            Log.log_debug_1(f"Invalid quest: {quest}")
            return False
        
        if not (quest.name in cfg.config.quest.quests):
            Log.log_debug_1(f"Quest {quest.quest_id}/{quest.name} is not in config.")
            return False
        
        if quest.category.is_repair():
            Log.log_debug_1(f"Quest {quest.quest_id}/{quest.name} is a repair/supply quest, which is always enabled.")
            return True
        
        quest_dict = kca_u.kca.get_quest_count(target_quest= quest)

        force_enable = False
        if self.auto_select_quest[context] != None and quest.quest_id == self.auto_select_quest[context].quest_id:
            force_enable = True
        
        if context == CONTEXT_SORTIE:
            if quest.category.is_sortie() == False:
                Log.log_debug_1(f"Quest {quest.name} {quest.category} is not a combat quest.")
                return False
            if len(com.combat.get_sortie_queue()) <= 0:
                Log.log_msg("No sortie quests available, cannot activate sortie quest.")
                return False
            elif quest.map_context != ():
                if quest_dict:
                    if not (com.combat.get_sortie_queue()[0].without_quest_enum in quest_dict.keys()):
                        Log.log_debug_1(f"Quest {quest.name} is not relevant to sortie map {com.combat.get_sortie_queue()[0].without_quest} anymore.")
                        return False
                elif not (com.combat.get_sortie_queue()[0].without_quest_enum in quest.map_context):
                    Log.log_debug_1(f"Quest {quest.name} is not relevant to sortie map {com.combat.get_sortie_queue()[0].without_quest}.")
                    return False
            elif quest.enemy_context != () and not (set(com.combat.map_data.enemy_context) & set(quest.enemy_context)):
                Log.log_debug_1(f"Quest {quest.name} is not relevant to enemy context {com.combat.map_data.enemy_context}.")
                return False
            elif quest.fleet_composition != {} and not self._is_fleet_valid_for_quest(quest, flt.fleets.combat_fleets[0]):
                Log.log_debug_1(f"Fleet layout is not valid for quest {quest.name}.")
                if force_enable == True:
                    Log.log_error(f"Fleet layout is not valid for quest {quest.name}.")
                    Log.log_warn(f"Quest {quest.name} is the current target quest for {self.CONTEXT_LOOKUP[context]}, force enabling it.")
                else:
                    return False
            
            return True
        elif context == CONTEXT_EXPEDITION:
            if quest.category.is_expedition() == False:
                Log.log_debug_1(f"Quest {quest.name} {quest.category} is not an expedition quest.")
                return False
            
            if quest.exp_context != ():
                if quest_dict:
                    if not any(expedition in exp.expedition.cur_exp for expedition in quest_dict.keys()):
                        Log.log_debug_1(f"Quest {quest.name} is not relevant to expedition {exp.expedition.cur_exp} anymore.")
                        return False
                elif not any(item in exp.expedition.cur_exp for item in quest.exp_context):
                    Log.log_debug_1(f"Quest {quest.name} is not relevant to expedition {exp.expedition.cur_exp}.")
                    return False
                
            return True
        elif context == CONTEXT_PVP:
            if quest.category.is_pvp() == False:
                Log.log_debug_1(f"Quest {quest.name} {quest.category} is not a PVP quest.")
                return False
            elif quest.fleet_composition != {} and not self._is_fleet_valid_for_quest(quest, flt.fleets.pvp_fleets[0]):
                Log.log_debug_1(f"Fleet layout is not valid for quest {quest.name}.")
                if force_enable == True:
                    Log.log_error(f"Fleet layout is not valid for quest {quest.name}.")
                    Log.log_warn(f"Quest {quest.name} is the current target quest for {self.CONTEXT_LOOKUP[context]}, force enabling it.")
                    return True
                else:
                    return False
            else:
                return True
        elif context == CONTEXT_FACTORY:
            if quest.category.is_factory() == False:
                Log.log_debug_1(f"Quest {quest.name} {quest.category} is not a factory quest.")
                return False
            else:
                return True
        elif context == None:
            return False
        else:
            Log.log_error(f"Unknown context {self.CONTEXT_LOOKUP[context]}.")
            return False
        
    def _is_fleet_valid_for_quest(self, quest : Quest, fleet : flt.Fleet):
        """Check if a fleet is valid for a given quest."""
        
        for requirement_list in quest.fleet_composition:
            for requirement in quest.fleet_composition[requirement_list] :
                
                position = [0,1,2,3,4,5,6]
                amount = 1
                count_rule = self.AT_LEAST
                if self.POSITION in requirement:
                    position = requirement[self.POSITION]
                if self.AMOUNT in requirement:
                    amount = requirement[self.AMOUNT]
                if self.COUNT_RULE in requirement:
                    count_rule = requirement[self.COUNT_RULE]
                    
                if self.ID in requirement:
                    count = fleet.has_id(requirement[self.ID], position)
                elif self.STYPE in requirement:
                    count = fleet.has_stype([ShipTypeEnum(ship_type) for ship_type in requirement[self.STYPE]], position)
                elif self.CTYPE in requirement:
                    count = fleet.has_ctype([ShipClassEnum(ship_class) for ship_class in requirement[self.CTYPE]], position)
                elif self.ALLOWED_SHIP_TYPES in requirement:
                    if fleet.has_stype(requirement[self.ALLOWED_SHIP_TYPES], [0,1,2,3,4,5,6]) != fleet.size:
                        return False
                                
                if count_rule == self.AT_LEAST and count < amount:
                    return False
                elif count_rule == self.AT_MOST and count > amount:
                    return False
                elif count_rule == self.EXACT and count != amount:
                    return False
                
        return True
    
    def is_tracking_quest(self, quest : Quest):
        """Check if a quest is being tracked."""
        return quest.quest_id in self.next_check_intervals

quest = QuestCore()
