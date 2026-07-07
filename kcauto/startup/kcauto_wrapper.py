import traceback
from util.pyvisauto import FindFailed
from time import sleep

import startup.kcauto as _
import args.args_core as arg
from constants import LOOP_BREAK_SECONDS
from util.exceptions import ApiException, Catbomb201Exception, ChromeCrashException
from util.logger import Log
from util.recovery import Recovery
import ships.equipment_core as equ


def get_poi_quest_stats():
    import util.kca as kca_u
    import json

    Log.log_debug_1("正在從 poi 大腦提取精確任務統計數據...")

    # 💡 只拿 store.info.quests，資料量小又極度精準
    js_code = """
    (() => {
        try {
            const store = window.getStore();
            if (store && store.info && store.info.quests) {
                // store.info.quests 內包含了當前所有任務的即時精確計數
                return JSON.stringify(store.info.quests);
            }
            return "{}";
        } catch (e) {
            return JSON.stringify({error: e.message});
        }
    })()
    """

    try:
        response = kca_u.kca.poi_hook.Runtime.evaluate(
            expression=js_code, returnByValue=True
        )

        # 💡 解除 Tuple 限制：如果回傳是 list 或 tuple，我們取第一個元素
        if isinstance(response, (list, tuple)) and len(response) > 0:
            resp_dict = response[0]
        else:
            resp_dict = response

        # 精準解析兩層嵌套的 ["result"]["result"]["value"]
        if resp_dict and "result" in resp_dict and "result" in resp_dict["result"]:
            raw_json = resp_dict["result"]["result"].get("value", "{}")
            poi_quests = json.loads(raw_json)
            # print(poi_quests)
            return poi_quests
        else:
            Log.log_error("無法成功解析 CDP 回傳的資料結構。")
            return {}

    except Exception as e:
        Log.log_error(f"提取 poi 任務失敗: {str(e)}")
        return {}


def kcauto_main():
    """Primary method that contains kcauto and various recovery logic."""
    active_loop = True
    kca_loop = True
    while active_loop:
        try:
            # startup methods
            _.kcauto.start_kancolle()
            _.kcauto.find_kancolle()

            while kca_loop:
                # primary logic
                _.kcauto.hook_health_check()
                _.kcauto.check_config()
                if _.kcauto.scheduler_kca_active:
                    # if first_loop == True:

                    get_poi_quest_stats()

                    Log.log_debug_1("New kca_loop started")

                    _.kcauto.initialization_check()
                    _.kcauto.run_expedition_logic()
                    _.kcauto.run_factory_logic()
                    _.kcauto.run_pvp_logic()
                    _.kcauto.run_combat_logic()

                    _.kcauto.run_repair_logic(passive_only=True)
                    _.kcauto.run_shipswitch_logic()
                    _.kcauto.check_end_loop_at_port()
                    _.kcauto.print_stats()
                _.kcauto.run_scheduler()
                sleep(LOOP_BREAK_SECONDS)
        except FindFailed:
            Log.log_error("FindFailed stacktrace:")
            print(traceback.format_exc())
            Log.log_error("End stacktrace.")
            if not Recovery.attempt_recovery():
                Log.log_error("Recovery failed. Shutting down kcauto.")
                active_loop = False
        except ApiException:
            Log.log_error("ApiException stacktrace:")
            print(traceback.format_exc())
            Log.log_error("End stacktrace.")
            if not Recovery.recovery_from_catbomb():
                Log.log_error("Recovery failed. Shutting down kcauto.")
                active_loop = False
        except Catbomb201Exception:
            Log.log_error("Catbomb201Exception stacktrace:")
            print(traceback.format_exc())
            Log.log_error("End stacktrace.")
            if not Recovery.recovery_from_catbomb(catbomb_201=True):
                Log.log_error("Recovery failed. Shutting down kcauto.")
                active_loop = False
        except ChromeCrashException:
            Log.log_error("ChromeCrashException stacktrace:")
            print(traceback.format_exc())
            Log.log_error("End stacktrace.")
            if not Recovery.recovery_from_chrome_crash(crash_type=2):
                Log.log_error("Recovery failed. Shutting down kcauto.")
                active_loop = False
