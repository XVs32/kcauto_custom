from kca_enums.enum_base import EnumBase


class ShipTypeEnum(EnumBase):
    NA = 0
    DE = 1
    DD = 2
    CL = 3
    CLT = 4
    CA = 5
    CAV = 6
    CVL = 7
    FBB = 8
    BB = 9
    BBV = 10
    CV = 11
    SD = 12 #Super Dreadnoughts, unuse at the moment
    SS = 13
    SSV = 14
    EAO = 15 #enemy AO
    AV = 16
    LHA = 17
    CVB = 18
    AR = 19
    AS = 20
    CT = 21
    AO = 22

    @property
    def type(self):
        return self.name

    @property
    def display_name(self):
        return self.name

    @property
    def id(self):
        return self.value
    
    @property
    def count(self):
        return 23