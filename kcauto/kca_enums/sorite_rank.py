from kca_enums.enum_base import EnumBase


class SortieRankEnum(EnumBase):
    S = 5
    A = 4
    B = 3
    C = 2
    D = 1
    E = 0

    @property
    def in_str(self):
        return self.name.title()
    
    @property
    def in_int(self):
        return self.value
    
    def is_at_least(self, target_rank_enum: "SortieRankEnum") -> bool:
        """Check if the current rank is at least the target rank."""
        return self.value >= target_rank_enum.value
