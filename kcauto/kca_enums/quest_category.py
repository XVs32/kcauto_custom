from kca_enums.enum_base import EnumBase

class QuestCategoryEnum(EnumBase):
    UNDEFINED = 0
    ORGANISATION = 1
    SORTIE = 2
    PVP = 3
    EXPEDITION = 4
    REPAIR = 5
    FACTORY = 6
    AKASHI = 7
    SORTIE_2 = 8
    SORTIE_3 = 9
    SORTIE_4 = 10
    FACTORY_1 = 11
    
    def is_sortie(self):
        return self in (self.SORTIE, self.SORTIE_2, self.SORTIE_3, self.SORTIE_4)
    def is_expedition(self):
        return self == self.EXPEDITION
    def is_factory(self):
        return self in (self.FACTORY, self.FACTORY_1)
    def is_pvp(self):
        return self == self.PVP
    def is_repair(self):
        return self == self.REPAIR
    def is_organisation(self):
        return self == self.ORGANISATION
    def is_akashi(self):
        return self == self.AKASHI