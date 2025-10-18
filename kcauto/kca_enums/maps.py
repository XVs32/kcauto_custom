
from kca_enums.enum_base import EnumBase
import json
class MapEnum_t(EnumBase):
    @property
    def quest(self):
        if len(self.value.split("-")[0]) > 1:
            return self.value.split("-")[0][1:]
        
        return None
    
    @property
    def world(self):
        world = self.value.split("-")[1]
        if world == "E":
            return world
        return int(world)

    @property
    def map(self):
        return int(self.value.split("-")[2])

    @property
    def world_and_map(self):
        if self.value != "auto":
            return self.value.split("-")[1] + "-" + self.value.split("-")[2] 
        else:
            return "auto"

    @property
    def world_and_map_and_node(self):
        if self.value != "auto":
            return self.value[self.value.index("-")+1:]
        else:
            return "auto"
        
    @property
    def without_quest(self):
        if self.value != "auto":
            #find the first "-"
            return f'B{self.value[self.value.index("-"):]}'
        else:
            return "auto"
        
    @property
    def without_quest_enum(self):
        if self.value != "auto":
            #find the first "-"
            return self.__class__("B" + self.value[self.value.index("-"):])
        else:
            return self.__class__.auto_map_select
        
    @property
    def without_quest_and_node(self):
        if self.value != "auto":
            return "B-" + self.value.split("-")[1] + "-" + self.value.split("-")[2] 
        else:
            return "auto"
            
    @property
    def without_quest_and_node_enum(self):
        if self.value != "auto":
            return self.__class__("B-" + self.value.split("-")[1] + "-" + self.value.split("-")[2]) 
        else:
            return self.__class__.auto_map_select
            
    @property
    def is_map_variant(self):
        return len(self.value.split("-")) > 3

    @property
    def variant(self):
        if self.is_map_variant:
            return self.value.split("-")[3]
        else:
            return None
            
# ----------------------------------------------------
# 2. 數據源 (JSON) 讀取邏輯
# ----------------------------------------------------
# 假設這是從實際檔案讀取的
try:
    with open('data/combat/map_enum.json', 'r', encoding='utf-8') as f:
        data_dict = json.load(f)
except FileNotFoundError:
    # 作為範例，如果找不到檔案，使用預設值
    print("Warning: config_status.json not found, using hardcoded defaults.")
    data_dict = {
        "STATUS_OK": 200,
        "STATUS_ERROR": 500,
        "STATUS_PENDING": 100
    }

# ----------------------------------------------------
# 3. 動態類別創建 (在模組層級執行)
# ----------------------------------------------------
# 使用 type() 函式創建並賦值給一個全域變數
MapEnum = MapEnum_t(
    'MapEnum', 
    data_dict             
)