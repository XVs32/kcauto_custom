from kca_enums.expeditions import ExpeditionEnum
from kca_enums.quest_category import QuestCategoryEnum
from util.json_data import JsonData
from kca_enums.maps import MapEnum
from kca_enums.quest_type import QuestTypeEnum
from kca_enums.quest_state import QuestStateEnum
from kca_enums.sorite_rank import SortieRankEnum
from util.logger import Log



class Quest(object):
    
    name: str | None = None
    quest_id: int | None = None
    
    category: 'QuestCategoryEnum | None' = None
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
            self.category = QuestCategoryEnum(api_data.get('api_category', None))
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
            
        if api_data is None:
            self.category = self._get_category_from_static_data()
            self.quest_type = self._get_type_from_static_data()
        
    @property
    def intervals(self):
        return tuple(Quest.static_data[self.name].get('intervals', (0, 0, 0)))
    
        
    @property
    def enemy_context(self):
        return tuple(Quest.static_data[self.name].get('enemy_context', ()))
        
    @property
    def map_context(self) -> tuple[MapEnum, ...]:
        return tuple(MapEnum(m.get('name','')) for m in Quest.static_data[self.name].get('map_context', []))
    
    @property
    def rank_requirement(self):
        ret = {}
        for map in Quest.static_data[self.name].get('map_context', []):
            ret[MapEnum(map.get('name',''))] = SortieRankEnum[map.get('min_rank','E')]
        
        return ret
        
    @property
    def exp_context(self):
        return tuple(ExpeditionEnum(e) for e in Quest.static_data[self.name].get('expedition_context', []))
        
    @property
    def recommended_map(self):
        ret = []
        for map in Quest.static_data[self.name].get('recommended_map', []):
            ret.append(MapEnum(map))
        return tuple(ret)
    
    @property
    def fleet_composition(self):
        return Quest.static_data[self.name].get('fleet_composition', {})
    
    def _get_quest_id(self, name):
        quest = Quest.static_data.get(name, None)
        if quest != None:
            return quest['id']
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
 
    def _get_category_from_static_data(self):
        """Get the quest category from static data."""
        
        name = self.name
        if self.name[0:4].isdigit() == True:
            name = self.name[4:]
        
        if name[0] == "B":
            return QuestCategoryEnum.SORTIE
        elif name[0] == "C":
            return QuestCategoryEnum.PVP
        elif name[0] == "D":   
            return QuestCategoryEnum.EXPEDITION
        elif name[0] == "E":
            return QuestCategoryEnum.REPAIR
        elif name[0] == "F":
            return QuestCategoryEnum.FACTORY
    
    def _get_type_from_static_data(self):
        """Get the quest type from static data."""
        if self.name in Quest.static_data:
            if Quest.static_data[self.name].get('type', None) == "daily":
                return QuestTypeEnum.DAILY
            elif Quest.static_data[self.name].get('type', None) == "weekly":
                return QuestTypeEnum.WEEKLY
            elif Quest.static_data[self.name].get('type', None) == "monthly":
                return QuestTypeEnum.MONTHLY
            elif Quest.static_data[self.name].get('type', None) == "single":
                return QuestTypeEnum.SINGLE
            elif Quest.static_data[self.name].get('type', None) == "other":
                return QuestTypeEnum.OTHER
        else:
            return None
        
    def __repr__(self):
        return f"{self.name} (#{self.quest_id})"
