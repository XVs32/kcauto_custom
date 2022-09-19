import config.config_core as cfg
from stats.stats_base import StatsBase
from util.logger import Log


class FactoryStats(StatsBase):
    work_phase= 0

    def __init__(self, start_time):
        super().__init__(start_time)
        Log.log_debug("Factory Stats module initialized.")

    def next_phase(self):
        self.work_phase += 1

    def current_phase(self):
        return self.work_phase