import time
import config.config_core as cfg
import nav.nav as nav
import util.kca as kca_u
from util.logger import Log


class FactoryCore(object):
    enabled = False
    disable_timer = 0
    order_oil_region        = {1    : "order_oil_region_1",
                               10   : "order_oil_region_10",
                               100  : "order_oil_region_100"}
    order_ammo_region       = {1    : "order_ammo_region_1",
                               10   : "order_ammo_region_10",
                               100  : "order_ammo_region_100"}
    order_steel_region      = {1    : "order_steel_region_1",
                               10   : "order_steel_region_10",
                               100  : "order_steel_region_100"}
    order_bauxite_region    = {1    : "order_bauxite_region_1",
                               10   : "order_bauxite_region_10",
                               100  : "order_bauxite_region_100"}
    order_resource_region   = [order_oil_region,
                               order_ammo_region,
                               order_steel_region,
                               order_bauxite_region]

    def __init__(self):
        self.enabled = cfg.config.factory.enabled
        pass

    def set_timer(self):
        self.disable_timer = time.time()

    def disable_time_up(self):
        return time.time() > self.disable_timer + (60 * 60)

    def develop_logic(self, count):
        self.goto()
        oil, ammo, steel, bauxite = self.read_config_develop()
        return self.develop(oil, ammo, steel, bauxite, count)
        

    def build_logic(self, count):
        self.goto()
        oil, ammo, steel, bauxite = self.read_config_build()
        return self.build(oil, ammo, steel, bauxite, count)

    def goto(self):
        nav.navigate.to('development')

    def develop(self, oil, ammo, steel, bauxite, count):
        """Place the develop order"""
        """Assume currently at factory page when called"""

        while count > 0:

            """click develop"""
            retry = 0
            while not kca_u.kca.exists(
                'lower', "factory|develop_menu.png") and retry < 5:
                kca_u.kca.r["develop_region"].click()
                kca_u.kca.sleep(1)
                retry += 1

            if retry == 5:
                Log.log_error("Cannot open develop menu, probably because the port is full.")
                Log.log_error("Disabling factory module.")
                self.enabled = False
                return False

            resource_list = [oil, ammo, steel, bauxite]

            for i in range(4):
                """The init 10 point of resource on the order"""
                resource = resource_list[i]
                resource -= 10
                while resource >= 100:
                    kca_u.kca.r[self.order_resource_region[i][100]].click()
                    resource -= 100
                while resource >= 10:
                    kca_u.kca.r[self.order_resource_region[i][10]].click()
                    resource -= 10
                while resource >= 1:
                    kca_u.kca.r[self.order_resource_region[i][1]].click()
                    resource -= 1

            if count >= 3:
                """click triple develop"""
                kca_u.kca.r["use_item_region"].click()
                count -= 3
            else:
                count -= 1
            
            kca_u.kca.r["order_confirm_region"].click()
            kca_u.kca.wait('lower_right_corner', 'global|next_alt.png', 20)
            while not kca_u.kca.exists('left', 'nav|side_menu_home.png'):
                Log.log_debug_1("In develop result")
                kca_u.kca.r['shipgirl'].click()
                kca_u.kca.r['top'].hover()

        return True
    
    def any_build_slot_available(self):
        """return false if both slots are occupied"""
        if  kca_u.kca.exists("build_slot_1_stat_region",
                            "factory|build_progressing.png")\
            and \
            kca_u.kca.exists("build_slot_2_stat_region",
                            "factory|build_progressing.png"):
            return False
        else:
            return True

    def build(self, oil, ammo, steel, bauxite, count):
        """Place the build order"""
        """Assume currently at factory page when called"""
        
        init_resource = [30, 30, 30, 30]
        step_multiplier = 1
            
        while count > 0:

            kca_u.kca.sleep(1)
            if self.any_build_slot_available() == False:
                return False

            build_slot_stat = {1:"build_slot_1_stat_region",
                               2:"build_slot_2_stat_region"}
            build_slot = {1:"build_slot_1_region",
                          2:"build_slot_2_region"}

            """receive if a build is done"""
            for i in range(1,3):
                if kca_u.kca.exists(build_slot_stat[i],
                                    "factory|build_finish.png"):
                    kca_u.kca.r[build_slot[i]].click()

                    kca_u.kca.sleep(1)
                    retry = 0
                    while not kca_u.kca.exists(
                        build_slot_stat[i], "factory|build_idle.png")\
                        and retry < 10:
                        kca_u.kca.r[build_slot_stat[i]].click()
                        kca_u.kca.sleep(3)
                        retry += 1

                    if retry == 10:
                        Log.log_error("Cannot receive ship, probably because the port is full.")
                        Log.log_error("Disabling factory module.")
                        self.enabled = False
                        return False
                    
                    while not kca_u.kca.exists('left', 'nav|side_menu_home.png'):
                        kca_u.kca.r['shipgirl'].click()
                        kca_u.kca.r['top'].hover()
                    kca_u.kca.wait('lower', 'factory|factory_init.png', 20)

            """place the order on a empty slot"""
            for j in range(1,3):
                if kca_u.kca.exists(build_slot_stat[j],
                                    "factory|build_idle.png"):
                    """click build slot"""
                    retry = 0
                    while not kca_u.kca.exists(
                        'lower', "factory|develop_menu.png") and retry < 5:
                        kca_u.kca.r[build_slot[j]].click()
                        kca_u.kca.sleep(1)
                        retry += 1

                    if retry == 5:
                        Log.log_error("Cannot open develop menu, probably because the port is full.")
                        Log.log_error("Disabling factory module.")
                        self.enabled = False
                        return False

                    if self.is_large_ship_construction(oil, ammo, steel, bauxite) == True:
                        kca_u.kca.click_existing("lower", "factory|large_ship_construction.png")
                        kca_u.kca.click_existing("lower", "factory|large_ship_construction_agree.png")
                        init_resource = [1500, 1500, 2000, 1000]
                        step_multiplier = 10
                        
                    resource_list = [oil, ammo, steel, bauxite]

                    for i in range(4):
                        """The init 30 point of resource on the order"""
                        resource = resource_list[i]
                        resource -= init_resource[i]
                        
                        while resource >= 100 * step_multiplier:
                            kca_u.kca.r[self.order_resource_region[i][100]].click()
                            resource -= 100 * step_multiplier 
                        while resource >= 10 * step_multiplier:
                            kca_u.kca.r[self.order_resource_region[i][10]].click()
                            resource -= 10 * step_multiplier
                        while resource >= 1 * step_multiplier:
                            kca_u.kca.r[self.order_resource_region[i][1]].click()
                            resource -= 1 * step_multiplier

                    kca_u.kca.r["order_confirm_region"].click()
                    kca_u.kca.wait('lower', 'factory|factory_init.png', 20)
                    
                    count -= 1
                    if count <= 0:
                        break

        """all requested build seccessfully done"""
        return True
                
    def read_config_develop(self):
        oil     = cfg.config.factory.develop["recipe"][0]
        ammo    = cfg.config.factory.develop["recipe"][1]
        steel   = cfg.config.factory.develop["recipe"][2]
        bauxite = cfg.config.factory.develop["recipe"][3]
        return oil, ammo, steel, bauxite
        
    def read_config_build(self):
        oil     = cfg.config.factory.build["recipe"][0]
        ammo    = cfg.config.factory.build["recipe"][1]
        steel   = cfg.config.factory.build["recipe"][2]
        bauxite = cfg.config.factory.build["recipe"][3]
        return oil, ammo, steel, bauxite


    def is_large_ship_construction(self, oil, ammo, steel, bauxite):
        """Check if the large ship construction is enabled"""
        if oil > 999 or ammo > 999 or steel > 999 or bauxite > 999:
            return True
        
        return False

factory = FactoryCore()
