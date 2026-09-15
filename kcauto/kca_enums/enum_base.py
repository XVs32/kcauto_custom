from enum import Enum


class EnumBase(Enum):
    @property
    def display_name(self):
        return self.value

    @classmethod
    def contains_value(cls, value):
        if value in cls._value2member_map_:
            return True
        return False

    @classmethod
    def get_default(cls):
        return next(iter(cls.__members__.items()))

    @classmethod
    def get_by_value(cls, value):
        if cls.contains_value(value):
            return cls(value)
        return cls.get_default()
