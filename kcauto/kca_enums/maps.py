from kca_enums.enum_base import EnumBase


class MapEnum(EnumBase):
    W1_1, W1_2, W1_3, W1_4, W1_5 = '1-1', '1-2', '1-3', '1-4', '1-5'
    W1_6 = '1-6'
    W2_1, W2_2, W2_3, W2_4, W2_5 = '2-1', '2-2', '2-3', '2-4', '2-5'
    W2_2_A = '2-2-A'
    W3_1, W3_2, W3_3, W3_4, W3_5 = '3-1', '3-2', '3-3', '3-4', '3-5'
    W4_1, W4_2, W4_3, W4_4, W4_5 = '4-1', '4-2', '4-3', '4-4', '4-5'
    W5_1, W5_2, W5_3, W5_4, W5_5 = '5-1', '5-2', '5-3', '5-4', '5-5'
    W6_1, W6_2, W6_3, W6_4, W6_5 = '6-1', '6-2', '6-3', '6-4', '6-5'
    W7_1, W7_2, W7_3, W7_4, W7_5 = '7-1', '7-2', '7-3', '7-4', '7-5'
    W7_2_1 = '7-2-1'
    W7_2_2 = '7-2-2'
    W7_3_1 = '7-3-1'
    W7_3_2 = '7-3-2'
    WE_1, WE_2, WE_3, WE_4, WE_5 = 'E-1', 'E-2', 'E-3', 'E-4', 'E-5'
    WE_6, WE_7, WE_8 = 'E-6', 'E-7', 'E-8'

    W1_5_Bw1 = '1-5-Bw1'
    W5_2_C = '5-2-C'
    W5_2_C_Bw1 = '5-2-C-Bw1'

    W2_5_Bm1 = '2-5-Bm1'
    W1_4_Bm3 = '1-4-Bm3'
    W5_1_Bm4 = '5-1-Bm4'
    W4_2_Bm6 = '4-2-Bm6'

    W2_5_Bm7 = "2-5-Bm7"

    W1_2_Bm8 = "1-2-Bm8"
    W1_3_Bm8 = "1-3-Bm8"
    W1_4_Bm8 = "1-4-Bm8"
    W2_1_Bm8 = "2-1-Bm8"
    
    W1_6_Bq3 = "1-6-Bq3"
    
    W6_3_Bq4 = "6-3-Bq4"
    
    W3_1_Bq5 = "3-1-Bq5"
    W3_2_Bq5 = "3-2-Bq5"
    W3_3_Bq5 = "3-3-Bq5"
    
    W5_4_Bq6 = "5-4-Bq6"
    
    W5_1_Bq7 = "5-1-Bq7"
    W5_3_Bq7 = "5-3-Bq7"
    W5_4_Bq7 = "5-4-Bq7"
    
    W1_3_Bq9 = "1-3-Bq9"
    W1_4_Bq9 = "1-4-Bq9"
    W2_1_Bq9 = "2-1-Bq9"
    W2_2_Bq9 = "2-2-Bq9"
    W2_3_Bq9 = "2-3-Bq9"
    
    
    W1_4_Bq11 = "1-4-Bq11"
    W2_1_Bq11 = "2-1-Bq11"
    W2_2_Bq11 = "2-2-Bq11"
    W2_3_Bq11 = "2-3-Bq11"
    
    W4_1_Bq12 = "4-1-Bq12"
    W4_2_Bq12 = "4-2-Bq12"
    W4_3_Bq12 = "4-3-Bq12"
    W4_4_Bq12 = "4-4-Bq12"
    W4_5_Bq12 = "4-5-Bq12"

    auto_map_selete = 'auto'

    @property
    def world(self):
        world = self.value.split('-')[0]
        if world == 'E':
            return world
        return int(world)

    @property
    def map(self):
        return int(self.value.split('-')[1])

    @property
    def world_and_map(self):
        if self.value != "auto":
            return self.value.split('-')[0] + "-" + self.value.split('-')[1] 
        else:
            return "auto"
