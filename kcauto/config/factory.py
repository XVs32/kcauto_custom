from config.config_base import ConfigBase

class ConfigFactory(ConfigBase):
    enabled = False
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