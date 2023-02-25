
from cui.macro import *

def set_config(config, reserve_slot):
    if reserve_slot == 0:
        config["passive_repair.enabled"] = False
    else:
        config["passive_repair.enabled"] = True
     
    config["passive_repair.slots_to_reserve"] = reserve_slot

    return
