

#open/create file called test.py
f = open("maps.py", "w", encoding='utf-8')

f.write('\n\
from kca_enums.enum_base import EnumBase\n\
\n\
class MapEnum(EnumBase):\n')


#read all .json file under data/combat folder
import os
import json
for file in os.listdir("../../data/combat"):
    if file.endswith(".json"):
        
        world = file.split("-")[0]
        stage = file.split("-")[1].split(".")[0]
        
        f.write("    W"+ str(world) + "_" + str(stage) + "=" +  "\"B-" + str(world) + "-" + str(stage) + "\"\n")
        #open file
        with open("../../data/combat/" + file, "r", encoding='utf-8') as map_json:
            #read file
            data = json.load(map_json)
            
            #get the map name
            
            nodes = []
            DISTINATION = 1
            NODE_NAME_MAX_LEN = 4
            for key in data["edges"]:
                
                #if not a node
                if len( data["edges"][key][DISTINATION]) > NODE_NAME_MAX_LEN:
                    continue
                
                nodes.append(data["edges"][key][DISTINATION])
                #write the following code to the file
                
            nodes = list(set(nodes))
            
            for node in nodes:
                f.write("    W"+ str(world) + "_" + str(stage)  + "_" + node + "=" +  "\"B-" + str(world) + "-" + str(stage) + "-" + node + "\"\n")

#write the following code to the file
f.write('\n\
\n\
    W1_1_Bw1 = "Bw1-1-1"\n\
    W1_5_Bw1 = "Bw1-1-5"\n\
    W5_2_C_Bw1 = "Bw1-5-2-C"\n\
\n\
    W2_5_Bm1 = "Bm1-2-5"\n\
    W1_4_Bm3 = "Bm3-1-4"\n\
    W5_1_Bm4 = "Bm4-5-1"\n\
    W4_2_Bm6 = "Bm6-4-2"\n\
\n\
    W2_5_Bm7 = "Bm7-2-5"\n\
\n\
    W1_2_Bm8 = "Bm8-1-2"\n\
    W1_3_Bm8 = "Bm8-1-3"\n\
    W1_4_Bm8 = "Bm8-1-4"\n\
    W2_1_Bm8 = "Bm8-2-1"\n\
    \n\
    W2_4_Bq3 = "Bq2-2-4"\n\
    W6_1_Bq3 = "Bq2-6-1"\n\
    W6_3_Bq3 = "Bq2-6-3"\n\
    W6_4_Bq3 = "Bq2-6-4"\n\
    W1_6_Bq3 = "Bq3-1-6"\n\
    \n\
    W6_3_Bq4 = "Bq4-6-3"\n\
    \n\
    W3_1_Bq5 = "Bq5-3-1"\n\
    W3_2_Bq5 = "Bq5-3-2"\n\
    W3_3_Bq5 = "Bq5-3-3"\n\
    \n\
    W5_4_Bq6 = "Bq6-5-4"\n\
    \n\
    W5_1_Bq7 = "Bq7-5-1"\n\
    W5_3_Bq7 = "Bq7-5-3"\n\
    W5_4_Bq7 = "Bq7-5-4"\n\
\n\
    W1_5_Bq8 = "Bq8-1-5"\n\
    W7_1_Bq8 = "Bq8-7-1"\n\
    W7_2_G_Bq8 = "Bq8-7-2-G"\n\
    W7_2_M_Bq8 = "Bq8-7-2-M"\n\
    \n\
    W1_3_Bq9 = "Bq9-1-3"\n\
    W1_4_Bq9 = "Bq9-1-4"\n\
    W2_1_Bq9 = "Bq9-2-1"\n\
    W2_2_Bq9 = "Bq9-2-2"\n\
    W2_3_Bq9 = "Bq9-2-3"\n\
    \n\
    \n\
    W1_4_Bq11 = "Bq11-1-4"\n\
    W2_1_Bq11 = "Bq11-2-1"\n\
    W2_2_Bq11 = "Bq11-2-2"\n\
    W2_3_Bq11 = "Bq11-2-3"\n\
    \n\
    W4_1_Bq12 = "Bq12-4-1"\n\
    W4_2_Bq12 = "Bq12-4-2"\n\
    W4_3_Bq12 = "Bq12-4-3"\n\
    W4_4_Bq12 = "Bq12-4-4"\n\
    W4_5_Bq12 = "Bq12-4-5"\n\
\n\
    W2_5_By1 = "By1-2-5"\n\
    W3_4_By1 = "By1-3-4"\n\
    W4_5_By1 = "By1-4-5"\n\
    W5_3_By1 = "By1-5-3"\n\
\n\
    W1_1_By2 = "By2-1-1"\n\
    W1_2_By2 = "By2-1-2"\n\
    W1_3_By2 = "By2-1-3"\n\
    W1_5_By2 = "By2-1-5"\n\
    W1_6_N_By2 = "By2-1-6-N"\n\
\n\
    W1_3_By3 = "By3-1-3"\n\
    W1_6_N_By3 = "By3-1-6-N"\n\
    W2_1_By3 = "By3-2-1"\n\
    W2_2_By3 = "By3-2-2"\n\
    W2_3_By3 = "By3-2-3"\n\
\n\
    W4_1_By4 = "By4-4-1"\n\
    W4_2_By4 = "By4-4-2"\n\
    W4_3_By4 = "By4-4-3"\n\
    W4_4_By4 = "By4-4-4"\n\
\n\
    W7_2_M_By5 = "By5-7-2-M"\n\
    W7_3_P_By5 = "By5-7-3-P"\n\
    W4_2_By5 = "By5-4-2"\n\
\n\
    W1_2_By6 = "By6-1-2"\n\
    W1_3_By6 = "By6-1-3"\n\
    W1_4_By6 = "By6-1-4"\n\
\n\
    W1_5_By7 = "By7-1-5"\n\
    W1_6_N_By7 = "By7-1-6-N"\n\
    W2_1_By7 = "By7-2-1"\n\
\n\
    W2_2_By8 = "By8-2-2"\n\
    W2_3_By8 = "By8-2-3"\n\
    W2_4_By8 = "By8-2-4"\n\
\n\
    W3_1_By9 = "By9-3-1"\n\
    W3_3_By9 = "By9-3-3"\n\
    W3_4_By9 = "By9-3-4"\n\
    W3_5_By9 = "By9-3-5"\n\
\n\
    W5_2_By10 = "By10-5-2"\n\
    W5_5_By10 = "By10-5-5"\n\
    W6_4_By10 = "By10-6-4"\n\
    W6_5_By10 = "By10-6-5"\n\
\n\
    W3_1_By11 = "By11-3-1"\n\
    W3_3_By11 = "By11-3-3"\n\
    W4_3_By11 = "By11-4-3"\n\
    W7_3_P_By11 = "By11-7-3-P"\n\
\n\
    W1_5_By12 = "By12-1-5"\n\
    W2_3_By12 = "By12-2-3"\n\
    W3_2_By12 = "By12-3-2"\n\
    W5_3_By12 = "By12-5-3"\n\
\n\
    auto_map_selete = "B-auto"\n\
\n\
    @property\n\
    def quest(self):\n\
        if len(self.value.split("-")[0]) > 1:\n\
            return self.value.split("-")[0][1:]\n\
        \n\
        return None\n\
    \n\
    @property\n\
    def world(self):\n\
        world = self.value.split("-")[1]\n\
        if world == "E":\n\
            return world\n\
        return int(world)\n\
\n\
    @property\n\
    def map(self):\n\
        return int(self.value.split("-")[2])\n\
\n\
    @property\n\
    def world_and_map(self):\n\
        if self.value != "auto":\n\
            return self.value.split("-")[1] + "-" + self.value.split("-")[2] \n\
        else:\n\
            return "auto"\n\
\n\
    @property\n\
    def without_quest(self):\n\
        if self.value != "auto":\n\
            #find the first "-"\n\
            return self.value[self.value.index("-")+1:]\n\
        else:\n\
            return "auto"\n\
        \n\
    @property\n\
    def is_map_variant(self):\n\
        return len(self.value.split("-")) > 3\n\
\n\
    @property\n\
    def variant(self):\n\
        if self.is_map_variant:\n\
            return self.value.split("-")[3]\n\
        else:\n\
            return None\n\
            \n')

#close the file
f.close()