import resource
from pyvisauto import Region
import api.api_core as api
import fleet.fleet_core as flt
import config.config_core as cfg
import nav.nav as nav
import stats.stats_core as sts
import util.kca as kca_u
from kca_enums.kcsapi_paths import KCSAPIEnum
from util.logger import Log


class FactoryCore(object):
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
        pass

    def develop_logic(self, count):
        self.goto()
        oil, ammo, steel, bauxite = self.read_config_develop()
        self.develop(oil, ammo, steel, bauxite, count)

    def goto(self):
        nav.navigate.to('development')

    def develop(self, oil, ammo, steel, bauxite, count):
        """Place the develop order"""
        """Assume currently at factory page when called"""

        while count > 0:

            """click develop"""
            while not kca_u.kca.exists(
                'lower', "factory|develop_menu.png"):
                kca_u.kca.r["develop_region"].click()
                kca_u.kca.sleep(1)

            resource_list = [oil, ammo, steel, bauxite]

            for i in range(4):
                """The init 10 point of resource on the order"""
                resource = resource_list[i]
                resource -= 10
                while resource >= 100:
                    print(self.order_resource_region[i][100])
                    kca_u.kca.r[self.order_resource_region[i][100]].click()
                    kca_u.kca.sleep
                    resource -= 100
                while resource >= 10:
                    print(self.order_resource_region[i][10])
                    kca_u.kca.r[self.order_resource_region[i][10]].click()
                    kca_u.kca.sleep
                    resource -= 10
                while resource >= 1:
                    print(self.order_resource_region[i][1])
                    kca_u.kca.r[self.order_resource_region[i][1]].click()
                    kca_u.kca.sleep
                    resource -= 1

            if count >= 3:
                """click triple develop"""
                kca_u.kca.click_existing(kca_u.kca.r["use_item_region"],"factory|do_not_use.png")
                count -= 3
            else:
                count -= 1
            
            kca_u.kca.r["order_confirm_region"].click()
            kca_u.kca.wait('lower_right_corner', 'global|next_alt.png', 20)
            while kca_u.kca.exists('lower_right_corner', 'global|next_alt.png'):
                kca_u.kca.sleep()
                kca_u.kca.r['shipgirl'].click()
                kca_u.kca.r['top'].hover()
                kca_u.kca.sleep()



    def read_config_develop(self):
        oil     = cfg.config.factory.develop["recipe"][0]
        ammo    = cfg.config.factory.develop["recipe"][1]
        steel   = cfg.config.factory.develop["recipe"][2]
        bauxite = cfg.config.factory.develop["recipe"][3]
        return oil, ammo, steel, bauxite
        





factory = FactoryCore()
