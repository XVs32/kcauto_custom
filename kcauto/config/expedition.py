from config.config_base import ConfigBase
import combat.combat_core as com
from kca_enums.expeditions import ExpeditionEnum
from kca_enums.fleet_modes import FleetModeEnum, CombinedFleetModeEnum
from util.json_data import JsonData


class ConfigExpedition(ConfigBase):
    _enabled = False
    _fleet_2 = []
    _fleet_3 = []
    _fleet_4 = []
    _fleet_preset = None
    
    _desire_oil = 0
    _desire_ammo = 0
    _desire_bauxite = 0
    _desire_steel = 0
    _desire_bucket = 0

    def __init__(self, config):
        super().__init__(config)
        self.enabled = config['expedition.enabled']
        all_expeditions = (
            config['expedition.fleet_2'] + config['expedition.fleet_3']
            + config['expedition.fleet_4'])
        if JsonData.has_str(all_expeditions) == False and len(all_expeditions) != len(set(all_expeditions)):
            raise ValueError("Conflicting expeditions assigned")
        self.fleet_2 = config.get('expedition.fleet_2', [])
        self.fleet_3 = config.get('expedition.fleet_3', [])
        self.fleet_4 = config.get('expedition.fleet_4', [])
        self.fleet_preset = config.get('expedition.fleet_preset', None)
        self.desire_oil = config.get('expedition.desire_oil', 350000)
        self.desire_ammo = config.get('expedition.desire_ammo', 350000)
        self.desire_bauxite = config.get('expedition.desire_bauxite', 350000)
        self.desire_steel = config.get('expedition.desire_steel', 350000)
        self.desire_bucket = config.get('expedition.desire_bucket', 3000)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        if type(value) is not bool:
            raise ValueError(
                "Specified value for expedition enabled is not a boolean.")
        self._enabled = value

    @property
    def fleet_2(self):
        return self._fleet_2

    @fleet_2.setter
    def fleet_2(self, value):
        if not self._validate_expeditions(value):
            raise ValueError(
                "Specified value for EXPEDITIONS_FLEET2 is not a valid exped")
        if (
                self._config['expedition.enabled']
                and len(value) > 0
                and self._config['combat.enabled']
                and CombinedFleetModeEnum.contains_value(
                    self._config['combat.fleet_mode'])):
            raise ValueError(
                "Fleet 2 cannot be assigned to expeditions when combat is CF")
        self._fleet_2 = [ExpeditionEnum(expedition) for expedition in value]

    @property
    def fleet_3(self):
        return self._fleet_3

    @fleet_3.setter
    def fleet_3(self, value):
        if not self._validate_expeditions(value):
            raise ValueError(
                "Specified value for EXPEDITIONS_FLEET3 is not a valid exped")
        if (
                self._config['expedition.enabled']
                and len(value) > 0
                and self._config['combat.enabled']
                and FleetModeEnum.STRIKE.value == self._config[
                    'combat.fleet_mode']):
            raise ValueError(
                "Fleet 3 cannot be assigned to expeditions when combat is +"
                " strike force")
        self._fleet_3 = [ExpeditionEnum(expedition) for expedition in value]

    @property
    def fleet_4(self):
        return self._fleet_4

    @fleet_4.setter
    def fleet_4(self, value):
        if not self._validate_expeditions(value):
            raise ValueError(
                "Specified value for EXPEDITIONS_FLEET4 is not a valid exped")
        self._fleet_4 = [ExpeditionEnum(expedition) for expedition in value]

    def expeditions_for_fleet(self, value):
        if not 1 < value < 5:
            raise ValueError("Invalid fleet id specified")
        return getattr(self, f'fleet_{value}')

    @property
    def all_expeditions(self):
        return self._fleet_2 + self._fleet_3 + self._fleet_4

    def _validate_expeditions(self, expeditions):
        for expedition in expeditions:
            if not ExpeditionEnum.contains_value(expedition):
                return False
        return True

    @property
    def expedition_fleets(self):
        expedition_fleets = []
        if len(self.fleet_2) > 0:
            expedition_fleets.append(2)
        if len(self.fleet_3) > 0:
            expedition_fleets.append(3)
        if len(self.fleet_4) > 0:
            expedition_fleets.append(4)
        return expedition_fleets
    
    @property
    def fleet_preset(self):
        return self._fleet_preset

    @fleet_preset.setter
    def fleet_preset(self, value):
        if not value:
            self._fleet_preset = None
        else:
            if value != "auto":
                raise ValueError("The only supported expedition preset is 'auto'/null at the moment.")
            self._fleet_preset = value

            
    @property
    def desire_oil(self):
        return self._desire_oil
    
    @desire_oil.setter
    def desire_oil(self, value):
        if type(value) is not int:
            raise ValueError("Specified value for desire_oil is not an integer.")
        self._desire_oil = value
        
    @property
    def desire_ammo(self):
        return self._desire_ammo
    @desire_ammo.setter
    def desire_ammo(self, value):
        if type(value) is not int:
            raise ValueError("Specified value for desire_ammo is not an integer.")
        elif value < 0 or value > 350000:
            raise ValueError("Specified value for desire_ammo is out of range (0-350000).")
        self._desire_ammo = value
        
    @property
    def desire_bauxite(self):
        return self._desire_bauxite
    @desire_bauxite.setter
    def desire_bauxite(self, value):
        if type(value) is not int:
            raise ValueError("Specified value for desire_bauxite is not an integer.")
        elif value < 0 or value > 350000:
            raise ValueError("Specified value for desire_bauxite is out of range (0-350000).")
        self._desire_bauxite = value
        
    @property
    def desire_steel(self):
        return self._desire_steel
    @desire_steel.setter
    def desire_steel(self, value):
        if type(value) is not int:
            raise ValueError("Specified value for desire_steel is not an integer.")
        elif value < 0 or value > 350000:
            raise ValueError("Specified value for desire_steel is out of range (0-350000).")
        self._desire_steel = value
        
    @property
    def desire_bucket(self):
        return self._desire_bucket
    @desire_bucket.setter
    def desire_bucket(self, value):
        if type(value) is not int:
            raise ValueError("Specified value for desire_bucket is not an integer.")
        elif value < 0 or value > 3000:
            raise ValueError("Specified value for desire_bucket is out of range (0-3000).")
        self._desire_bucket = value