from kca_enums.enum_base import EnumBase


class MapEnum(EnumBase):
    W1_1, W1_2, W1_3, W1_4, W1_5 = '1-1', '1-2', '1-3', '1-4', '1-5'
    W1_6 = '1-6'
    W2_1, W2_2, W2_3, W2_4, W2_5 = '2-1', '2-2', '2-3', '2-4', '2-5'
    W2_2_C = '2-2-C'
    W3_1, W3_2, W3_3, W3_4, W3_5 = '3-1', '3-2', '3-3', '3-4', '3-5'
    W4_1, W4_2, W4_3, W4_4, W4_5 = '4-1', '4-2', '4-3', '4-4', '4-5'
    W5_1, W5_2, W5_3, W5_4, W5_5 = '5-1', '5-2', '5-3', '5-4', '5-5'
    W6_1, W6_2, W6_3, W6_4, W6_5 = '6-1', '6-2', '6-3', '6-4', '6-5'
    W7_1, W7_2, W7_3, W7_4 = '7-1', '7-2', '7-3', '7-4'
    W7_2_1 = '7-2-1'
    W7_2_2 = '7-2-2'
    W7_3_1 = '7-3-1'
    W7_3_2 = '7-3-2'
    WE_1, WE_2, WE_3, WE_4, WE_5 = 'E-1', 'E-2', 'E-3', 'E-4', 'E-5'
    WE_6, WE_7, WE_8 = 'E-6', 'E-7', 'E-8'

    auto_map_selete = ''

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
        return self.value.split('-')[0] + "-" + self.value.split('-')[1] 
