from kca_enums.expeditions import ExpeditionEnum
from util.json_data import JsonData
from kca_enums.maps import MapEnum
from kca_enums.quest_type import QuestTypeEnum
from kca_enums.quest_state import QuestStateEnum
from util.logger import Log



class Quest(object):
    
    name = None
    quest_id = None
    
    category = None
    next_intervals = None
    
    completed_count = {}
    
    static_data = {}

    def __init__(self, name = None, quest_id = None, api_data = None):
        
        if Quest.static_data == {}:
            try:
                Quest.static_data = JsonData.load_json('data|quests|quests.json')
            except FileNotFoundError as e:
                Log.log_error("Quest data not found, please re-download it from github")
                Log.log_error(e)
                
        if api_data is not None:
            quest_id = api_data.get('api_no', None)
            self.category = api_data.get('api_category', None)
            self.quest_type = QuestTypeEnum(api_data.get('api_type', ''))
            self.state = QuestStateEnum(api_data.get('api_state', 0))
            self.title = api_data.get('api_title', '')
            self.select_rewards = api_data.get('api_select_rewards', None)
            
            
        if name != None:
            self.name = name
            self.quest_id = self._get_quest_id(name)
        elif quest_id != None:
            self.quest_id = quest_id
            self.name = self._get_name(quest_id) 
        
    @property
    def intervals(self):
        return tuple(Quest.static_data[self.name].get('intervals', (0, 0, 0)))
    
        
    @property
    def enemy_context(self):
        return tuple(Quest.static_data[self.name].get('enemy_context', ()))
        
    @property
    def map_context(self):
        return tuple(Quest.static_data[self.name].get('map_context', ()))
        
    @property
    def exp_context(self):
        return tuple([ExpeditionEnum(e) for e in Quest.static_data[self.name].get('expedition_context', [])])
        
    @property
    def recommended_map(self):
        return tuple(Quest.static_data[self.name].get('recommended_map', ()))
        
    def _get_quest_id(self, name):
        for quest_name in Quest.static_data:
            if quest_name == name:
                return Quest.static_data[quest_name]['id']
        return None

    def _get_name(self, quest_id):
        for quest_name in Quest.static_data:
            if Quest.static_data[quest_name]['id'] == quest_id:
                return quest_name
        return None
            
    def is_kcauto_support_quest(self):
        """Check if the quest is a KC-Auto supported quest."""
        if self.name is None or self.quest_id is None:
            return False
        return True
        
            
    def __repr__(self):
        return f"{self.name} (#{self.quest_id})"
