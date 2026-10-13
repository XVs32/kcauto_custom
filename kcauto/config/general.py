from config.config_base import ConfigBase
from kca_enums.interaction_modes import InteractionModeEnum
from constants import (
    DEFAULT_CHROME_DEV_PORT,
    DEFAULT_POI_API_PORT,
    DEFAULT_POI_CONTROL_PORT,
    MIN_JST_OFFSET,
    MAX_JST_OFFSET,
    MIN_PORT,
    MAX_PORT,
)


class ConfigGeneral(ConfigBase):
    _jst_offset = 0
    _interaction_mode = None
    _chrome_dev_port = DEFAULT_CHROME_DEV_PORT
    _poi_api_port = DEFAULT_POI_API_PORT
    _poi_control_port = DEFAULT_POI_CONTROL_PORT
    _debug_mode = False

    def __init__(self, config):
        super().__init__(config)
        self.jst_offset = config["general.jst_offset"]
        self.interaction_mode = config["general.interaction_mode"]
        self.chrome_dev_port = config.get("general.chrome_dev_port")
        self.poi_api_port = config.get("general.poi_api_port")
        self.poi_control_port = config.get("general.poi_control_port")

    @property
    def jst_offset(self):
        return self._jst_offset

    @jst_offset.setter
    def jst_offset(self, value):
        if not MIN_JST_OFFSET <= value <= MAX_JST_OFFSET:
            raise ValueError("Invalid JST offset")
        self._jst_offset = value

    @property
    def interaction_mode(self):
        return self._interaction_mode

    @interaction_mode.setter
    def interaction_mode(self, value):
        if not InteractionModeEnum.contains_value(value):
            raise ValueError("Invalid Interaction Mode")
        self._interaction_mode = InteractionModeEnum(value)

    @property
    def is_direct_control(self):
        return self.interaction_mode is InteractionModeEnum.DIRECT_CONTROL

    @property
    def chrome_dev_port(self):
        return self._chrome_dev_port

    @chrome_dev_port.setter
    def chrome_dev_port(self, value):
        if value is None:
            self._chrome_dev_port = DEFAULT_CHROME_DEV_PORT
            return
        elif type(value) is not int or not MIN_PORT <= value <= MAX_PORT:
            raise ValueError("Invalid Chrome Dev Port")
        self._chrome_dev_port = value

    @property
    def poi_api_port(self):
        return self._poi_api_port

    @poi_api_port.setter
    def poi_api_port(self, value):
        if value is None:
            self._poi_api_port = DEFAULT_POI_API_PORT
            return
        elif type(value) is not int or not MIN_PORT <= value <= MAX_PORT:
            raise ValueError("Invalid POI API Port")
        self._poi_api_port = value

    @property
    def poi_control_port(self):
        return self._poi_control_port

    @poi_control_port.setter
    def poi_control_port(self, value):
        if value is None:
            self._poi_control_port = DEFAULT_POI_CONTROL_PORT
            return
        elif type(value) is not int or not MIN_PORT <= value <= MAX_PORT:
            raise ValueError("Invalid POI Control Port")
        self._poi_control_port = value
