from config.config_base import ConfigBase
from kca_enums.ship_types import ShipTypeEnum

class ConfigFactory(ConfigBase):
    enabled = False
    develop_secretary = -1
    build_secretary = -1
    develop = {}
    build   = {}
    def __init__(self, config):
        super().__init__(config)
        self.enabled = config['factory.enabled']
        if type(self.enabled) is not bool:
            raise ValueError(
                "Specified value for factory enabled is not a boolean.")
        self.develop["recipe"]  = config['factory.develop_recipe']
        self.build["recipe"]    = config['factory.build_recipe']
        self.develop_secretary  = self._parse_secretary(config['factory.develop_secretary'])
        self.build_secretary    = self._parse_secretary(config['factory.build_secretary'])

    @staticmethod
    def _parse_secretary(value):
        if isinstance(value, str):
            try:
                return ShipTypeEnum[value.upper()]
            except KeyError:
                raise ValueError(f"Unknown ship type for secretary: {value!r}")
        return value