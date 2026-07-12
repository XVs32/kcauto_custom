import sys
from sys import platform
import os

from datetime import datetime, timedelta

import combat.combat_core as com
import combat.lbas_core as lbas
import expedition.expedition_core as exp
import ships.equipment_core as equ
from ships.equipment import Equipment as Equipment
import fleet.fleet_core as flt
import fleet_switcher.fleet_switcher_core as fsw
import pvp.pvp_core as pvp
import quest.quest_core as qst
import repair.repair_core as rep
import resupply.resupply_core as res
import ships.ships_core as shp
import stats.stats_core as sts
import util.kca as kca_u
from kca_enums.kcsapi_paths import KCSAPIEnum
from util.exceptions import ApiException, Catbomb201Exception, ChromeCrashException
from util.json_data import JsonData
from util.logger import Log
from constants import EMPTY_EQUIPMENT_API, TEMP_EQUIPMENT_API


class ApiWrapper(object):
    def __init__(self):
        Log.log_debug_1("API Wrapper module initialized.")
        self._pending_messages = []

    def update_from_api(
        self, target_apis={KCSAPIEnum.ANY}, process_all=True, timeout=30
    ):
        """
        Args: target_apis (set of KCSAPIEnum): Set of API endpoints to wait for. Use KCSAPIEnum.ANY to wait for any API, or KCSAPIEnum.NONE to skip waiting and return immediately. Default is KCSAPIEnum.ANY.
            process_all (bool): Whether to process all API messages received during the wait period (True) or just the first message for each target API (False). Default is True.
            timeout (int): Maximum time in seconds to wait for the target API payload(s). Default is 30 seconds.
        """
        if KCSAPIEnum.NONE in target_apis:
            return {}

        target_apis = set(target_apis)
        received_apis = set()

        Log.log_debug_1("Begin waiting for API payload(s).")
        kcapi_requests = {}
        results = {}
        end_time = datetime.now() + timedelta(seconds=timeout)

        while True:
            # Block waiting for a message. Use the remaining overall timeout
            # when one is set so we don't wake unnecessarily.
            remaining = (end_time - datetime.now()).total_seconds()
            if remaining <= 0:
                break
            wait_timeout = min(remaining, 1)

            first_message = kca_u.kca.api_hook.wait_message(timeout=wait_timeout)
            if first_message == None:
                first_message = []
            else:
                first_message = [first_message]

            # process the received message and any that have queued up
            self._pending_messages = (
                self._pending_messages + first_message + kca_u.kca.api_hook.pop_messages()
            )

            if not self._pending_messages:
                if len(target_apis) <= len(received_apis):
                    Log.log_debug_1("All target APIs received, ending wait.")
                    break
                # timed out waiting for a message; re-evaluate loop conditions
                continue

            if process_all == False and len(target_apis) <= len(received_apis):
                Log.log_debug_1("All target APIs received, ending wait.")
                break

            pending_id = 0
            for pending_id, message in enumerate(self._pending_messages):
                if message["method"] == "Network.responseReceived":
                    request_url = message["params"]["response"]["url"]
                    # found_target = None
                    for target_api in target_apis:
                        is_match = False
                        if target_api is KCSAPIEnum.MAP_INFO_JSON:
                            is_match = (
                                target_api.value in request_url
                                and request_url.split("?")[0].endswith(".json")
                            )
                        elif target_api is KCSAPIEnum.GAUGE:
                            is_match = True
                        elif target_api.value is not None:
                            is_match = (
                                target_api.value in request_url
                                and request_url.split("?")[0].endswith(
                                    target_api.value.split("/")[-1]
                                )
                            )

                        if is_match:
                            request_id = message["params"]["requestId"]
                            Log.log_debug_1(
                                f"Waiting for request {request_id} ({request_url})"
                            )
                            kcapi_requests[request_id] = {
                                "type": target_api,
                                "url": request_url,
                            }
                            break

                elif message["method"] == "Network.loadingFinished":
                    message_request_id = message["params"]["requestId"]
                    if message_request_id in kcapi_requests:
                        Log.log_debug_1(f"Request {message_request_id} received")
                        request_data = kcapi_requests.pop(message_request_id)
                        received_apis.add(request_data["type"])

                        response_body_attempt = 1
                        while True:
                            response_body = kca_u.kca.api_hook.Network.getResponseBody(
                                requestId=message_request_id
                            )
                            if response_body or response_body_attempt > 5:
                                break
                            Log.log_debug_1("Empty API response. Trying again.")
                            kca_u.kca.sleep(0.5)
                            response_body_attempt += 1

                        try:
                            if platform == "linux" or platform == "linux2":
                                raw_body = response_body[0]["result"]["body"]
                            elif platform == "darwin":
                                raw_body = response_body["result"]["body"]
                            elif platform == "win32":
                                raw_body = response_body[0]["result"]["body"]

                            raw_svdata = raw_body.removeprefix("svdata=")
                        except Exception:
                            raise ApiException("Empty or invalid API response.")

                        try:
                            parsed_data = JsonData.load_json_str(raw_svdata)
                        except Exception:
                            parsed_data = raw_svdata

                        res = self._load_api_data(request_data, parsed_data)

                        if request_data["type"].name in results:
                            results[request_data["type"].name].append(res)
                        else:
                            results[request_data["type"].name] = [res]

                        if not process_all and len(target_apis) <= len(received_apis):
                            break

            self._pending_messages = self._pending_messages[pending_id + 1 :]

        self._check_for_chrome_crash()

        return results

    def _check_for_chrome_crash(self):
        visual_events = kca_u.kca.api_hook.pop_messages()
        for event in visual_events:
            if event["method"] == "Inspector.targetCrashed":
                Log.log_warn("Chrome Crash detected.")
                raise ChromeCrashException

    def _load_api_data(self, request_data, data):
        request_type = request_data["type"]
        if "api_result" in data:
            if data["api_result"] != 1:
                Log.log_debug_1("Encountered non-1 API result.")
                Log.log_debug_1(data)
                if data["api_result"] == 201:
                    Log.log_error("Encountered catbomb.")
                    raise Catbomb201Exception
                else:
                    raise ApiException
        if request_type is KCSAPIEnum.GET_DATA:
            return self._process_get_data(data)
        elif request_type is KCSAPIEnum.REQUIRE_INFO:
            return self._process_require_info(data)
        elif request_type is KCSAPIEnum.PORT:
            return self._process_port(data)
        elif request_type is KCSAPIEnum.SORTIE_MAPS:
            return self._process_sortie_maps(data)
        elif request_type is KCSAPIEnum.SORTIE_START:
            return self._process_sortie_start(data)
        elif request_type is KCSAPIEnum.SORTIE_NEXT:
            return self._process_sortie_next(data)
        elif request_type is KCSAPIEnum.SORTIE_BATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_NIGHTBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_AIRBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_LD_AIRBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_LD_SHOOTING:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_N2D:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_NIGHT_ONLY:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_ECF_BATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_ECF_NIGHTBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_BATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_NIGHTBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_AIRBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_WATERBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_LD_AIRBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_LD_SHOOTING:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_N2D:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_NIGHT_ONLY:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_EACH_NIGHT_ONLY:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_ECF_BATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_ECF_AIRBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_ECF_WATERBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_ECF_LD_AIRBATTLE:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_ECF_LD_SHOOTING:
            return self._process_battle(data)
        elif request_type is KCSAPIEnum.SORTIE_RESULT:
            return self._process_battle_result(data)
        elif request_type is KCSAPIEnum.SORTIE_CF_RESULT:
            return self._process_battle_result(data)
        elif request_type is KCSAPIEnum.SORTIE_SHIPDECK:
            return self._process_battle_deck(data)
        elif request_type is KCSAPIEnum.SORTIE_END:
            return self._process_equipment_data(data)
        elif request_type is KCSAPIEnum.EXPEDITION_LIST:
            return self._process_expedition_list(data)
        elif request_type is KCSAPIEnum.EXPEDITION_START:
            return self._process_expedition_start(data)
        elif request_type is KCSAPIEnum.PVP_LIST:
            return self._process_pvp_list(data)
        elif request_type is KCSAPIEnum.PVP_ENEMY_INFO:
            return self._process_pvp_enemy_info(data)
        elif request_type is KCSAPIEnum.FLEETCOMP_PRESETS:
            return self._process_fleetcomp_presets(data)
        elif request_type is KCSAPIEnum.REPAIR_DOCKS:
            return self._process_repair_dock_data(data)
        elif request_type is KCSAPIEnum.QUEST_LIST:
            return self._process_quest_data(data)
        elif request_type is KCSAPIEnum.RESUPPLY_ACTION:
            return True
        elif request_type is KCSAPIEnum.LBAS_RESUPPLY_ACTION:
            return True
        elif request_type is KCSAPIEnum.FREE_EQUIPMENT:
            return self._process_free_equipment_data(data)
        elif request_type is KCSAPIEnum.MAP_INFO_JSON:
            return self._process_map_info_json(request_data)

        return None

    def _process_get_data(self, data):
        try:
            get_data_ship = data["api_data"]["api_mst_ship"]
            shp.ships.update_ship_library(get_data_ship)
            JsonData.dump_json(get_data_ship, "data|temp|get_data_ship.json")

            equ.equipment.reinforce_general_category = data["api_data"][
                "api_mst_equip_exslot"
            ]
            equ.equipment.reinforce_special = data["api_data"][
                "api_mst_equip_exslot_ship"
            ]
            equipment_static_data = data["api_data"]["api_mst_slotitem"]
            equipment_static_data.append(EMPTY_EQUIPMENT_API)
            equipment_static_data.append(TEMP_EQUIPMENT_API)
            JsonData.dump_json(
                equ.equipment.reinforce_general_category,
                "data|temp|reinforce_general_category.json",
            )
            JsonData.dump_json(
                equ.equipment.reinforce_special, "data|temp|reinforce_special.json"
            )
            JsonData.dump_json(equipment_static_data, "data|temp|equipment_static.json")
            Equipment.staic_data_reload()

            JsonData.dump_json(
                data["api_data"]["api_mst_stype"], "data|temp|ship_type.json"
            )
            JsonData.dump_json(
                data["api_data"]["api_mst_equip_ship"],
                "data|temp|equipment_ship_special.json",
            )

        except KeyError:
            Log.log_debug_1("No getData found in API response.")

        return None

    def _process_require_info(self, data):
        try:
            JsonData.dump_json(
                self._filter_equipment(data["api_data"]["api_slot_item"]),
                "data|temp|equipment_list.json",
            )
        except KeyError:
            Log.log_debug_1("No equipment found in API response.")

        try:
            exp_prov_resupply = data["api_data"]["api_extra_supply"][0] == 1
            res.resupply.exp_provisional_enabled = exp_prov_resupply
        except KeyError:
            Log.log_debug_1("No provisional resupply data found in API response")

    def _process_port(self, data):
        try:
            rsc_data = data["api_data"]["api_material"]
            sts.stats.rsc.update_resource_stats(rsc_data)
        except KeyError:
            Log.log_debug_1("No resource data found in API response.")

        try:
            ship_data = data["api_data"]["api_ship"]
            shp.ships.update_ship_pool(ship_data)
            JsonData.dump_json(ship_data, "data|temp|local_ship.json")
        except KeyError:
            Log.log_debug_1("No ship data found in API response.")

        try:
            fleet_data = data["api_data"]["api_deck_port"]
            flt.fleets.update_fleets(fleet_data)
            flt.fleets.load_custom_fleets()
            flt.fleets.load_custom_exp_pool()
            flt.fleets.load_idle_pool()
        except KeyError:
            Log.log_debug_1("No fleet data found in API response.")

        try:
            repair_data = data["api_data"]["api_ndock"]
            rep.repair.update_repair_data(repair_data)
        except KeyError:
            Log.log_debug_1("No repair data found in API response.")

        try:
            max_ships = data["api_data"]["api_basic"]["api_max_chara"]
            shp.ships.max_ship_count = max_ships
            max_equipment = data["api_data"]["api_basic"]["api_max_slotitem"]
            equ.equipment.max_equipment_count = max_equipment

        except KeyError:
            Log.log_debug_1("No ship count data found in API response.")

        try:
            max_quests = data["api_data"]["api_parallel_quest_count"]
            qst.quest.max_quests = max_quests
        except KeyError:
            Log.log_debug_1("No quest data found in API response.")

        try:
            from kca_enums.expeditions import ExpeditionEnum

            for i in range(1, len(data["api_data"]["api_deck_port"])):
                exp.expedition.cur_exp[i] = ExpeditionEnum(
                    data["api_data"]["api_deck_port"][i]["api_mission"][1]
                )
        except KeyError:
            Log.log_debug_1("No exp data found in API response.")

        try:
            from kca_enums.fleet_modes import FleetModeEnum

            combined_flag = data["api_data"]["api_combined_flag"]
            if combined_flag == 0:
                flt.fleets.combined_flag = FleetModeEnum.STANDARD
            elif combined_flag == 1:
                flt.fleets.combined_flag = FleetModeEnum.CTF
            elif combined_flag == 2:
                flt.fleets.combined_flag = FleetModeEnum.STF
            elif combined_flag == 3:
                flt.fleets.combined_flag = FleetModeEnum.TCF
        except KeyError:
            Log.log_debug_1("No combine_flag data found in API response.")

        import scheduler.scheduler_core as sch

        sch.scheduler.check_and_process_rules()

        return None

    def _process_sortie_maps(self, data):
        try:
            available_maps = data["api_data"]["api_map_info"]
            com.combat.update_combat_map_list(available_maps)
        except KeyError:
            Log.log_debug_1("No available combat map data in API response.")

        try:
            lbas_data = data["api_data"]["api_air_base"]
            lbas.lbas.update_lbas_groups(lbas_data)
        except KeyError:
            Log.log_debug_1("No available lbas data in API response.")

    def _process_sortie_start(self, data):
        try:
            select_nodes = data["api_data"]["api_select_route"]["api_select_cells"]
            com.combat.select_nodes = select_nodes
        except KeyError:
            Log.log_debug_1("No select node data found in API response.")

        try:
            edge_id = data["api_data"]["api_no"]
            com.combat.goto_next_node(edge_id)
            Log.log_msg(f"Moving to Node {com.combat.current_node}")
            return edge_id
        except KeyError:
            Log.log_debug_1("No next node data found in API response.")

    def _process_sortie_next(self, data):
        try:
            edge_id = data["api_data"]["api_no"]
            com.combat.goto_next_node(edge_id)
            Log.log_msg(f"Moving to Node {com.combat.current_node}")

            return edge_id
        except KeyError:
            Log.log_debug_1("No next node data found in API response.")

    def _process_battle(self, data):
        try:
            battle_data = data["api_data"]
            com.combat.predict_battle(battle_data)
        except KeyError:
            Log.log_debug_1("No battle data found in API response.")

    def _process_battle_result(self, data):
        try:
            result_data = data["api_data"]
            com.combat.process_battle_result(result_data)
        except KeyError:
            Log.log_debug_1("No CF battle data found in API response.")

    def _process_battle_deck(self, data):
        try:
            deck_data = data["api_data"]["api_ship_data"]
            shp.ships.update_ship_pool(deck_data)
            for fleet in flt.fleets.combat_fleets:
                fleet.update_ship_data()
        except KeyError:
            Log.log_debug_1("No CF battle data found in API response.")

    def _process_expedition_list(self, data):
        try:
            exp.expedition.available_expeditions = data["api_data"]["api_list_items"]
            exp.expedition.populate_available_expeditions_per_world()
        except KeyError:
            Log.log_debug_1("No expedition list data found in API response.")

        return None

    def _process_pvp_list(self, data):
        try:
            pvp_data = data["api_data"]["api_list"]
            pvp.pvp.update_pvp_list(pvp_data)
        except KeyError:
            Log.log_debug_1("No pvp data found in API response.")

        return None

    def _process_pvp_enemy_info(self, data):
        try:
            enemy_info = data["api_data"]["api_deck"]["api_ships"]
            return enemy_info
        except KeyError:
            Log.log_debug_1("No pvp enemy info data found in API response.")

    def _process_expedition_start(self, data):
        try:
            complete_time = data["api_data"]["api_complatetime"]
            return complete_time
        except KeyError:
            Log.log_debug_1("No expedition sent data")

        return None

    def _process_fleetcomp_presets(self, data):
        try:
            preset_data = data["api_data"]
            fsw.fleet_switcher.update_fleetpreset_data(preset_data)
        except KeyError:
            Log.log_debug_1("No fleetcomp preset data found in API response.")

    def _process_repair_dock_data(self, data):
        try:
            repair_data = data["api_data"]
            rep.repair.update_repair_data(repair_data)
        except KeyError:
            Log.log_debug_1("No repair data found in API response.")

    def _process_quest_data(self, data):
        try:
            quest_data = data["api_data"]
            qst.quest.update_quest_data(quest_data)
        except KeyError:
            Log.log_debug_1("No quest data found in API response.")

    def update_ship_library_from_json(self):
        try:
            ship_data = JsonData.load_json("data|temp|get_data_ship.json")
            shp.ships.update_ship_library(ship_data)
        except FileNotFoundError as e:
            Log.log_error(
                "get_data_ship.json not found. Please run kcauto from the "
                "Kancolle splash screen to download data."
            )
            Log.log_error(e)
            sys.exit(1)

    def _process_equipment_data(self, data):
        try:
            JsonData.dump_json(
                self._filter_equipment(data["api_data"]),
                "data|temp|equipment_list.json",
            )
        except KeyError:
            Log.log_debug_1("No equipment found in API response.")

    def _process_free_equipment_data(self, data):
        equ.equipment.equipment_pool[equ.equipment.RAW] = {}
        equ.equipment.equipment_pool[equ.equipment.FREE] = []
        try:
            equ.equipment.equipment_pool[equ.equipment.RAW] = data["api_data"][
                "api_slot_data"
            ]

            equipment_pool_temp: dict[str, list[Equipment]] = {}

            for key in equ.equipment.equipment_pool[equ.equipment.RAW]:
                equipment_pool_temp[key] = []

                for equipment_production_id in equ.equipment.equipment_pool[
                    equ.equipment.RAW
                ][key]:
                    equipment_temp = equ.equipment.get_equipment_by_production_id(
                        equ.equipment.equipment_pool[equ.equipment.ID],
                        equipment_production_id,
                    )
                    equipment_temp.category = int(key[len("api_slottype") :])
                    # Equipment.category_patch(equipment_temp.model_id, int(key[len("api_slottype"):]))
                    equipment_pool_temp[key].append(equipment_temp)

            keys = equ.equipment.equipment_pool[equ.equipment.RAW].keys()

            SECONDARY_GUN = "api_slottype4"
            EVENT_SECONDARY_GUN = "api_slottype95"
            if EVENT_SECONDARY_GUN in keys:
                Log.log_debug_1(
                    f"Found {EVENT_SECONDARY_GUN} in equipment pool, merging them"
                )

                temp = []

                secondary_gun_count = len(equipment_pool_temp[SECONDARY_GUN])
                event_secondary_gun_count = len(
                    equipment_pool_temp[EVENT_SECONDARY_GUN]
                )

                i = 0
                j = 0

                while i < secondary_gun_count and j < event_secondary_gun_count:
                    secondary_gun = equipment_pool_temp[SECONDARY_GUN][i]
                    event_secondary_gun = equipment_pool_temp[EVENT_SECONDARY_GUN][j]

                    if secondary_gun.model_id > event_secondary_gun.model_id:
                        temp.append(event_secondary_gun)
                        j += 1
                    else:
                        temp.append(secondary_gun)
                        i += 1

                while i < secondary_gun_count:
                    secondary_gun = equipment_pool_temp[SECONDARY_GUN][i]
                    temp.append(secondary_gun)
                    i += 1
                while j < event_secondary_gun_count:
                    event_secondary_gun = equipment_pool_temp[EVENT_SECONDARY_GUN][j]
                    temp.append(event_secondary_gun)

                equipment_pool_temp[SECONDARY_GUN] = temp
                del equipment_pool_temp[EVENT_SECONDARY_GUN]

            sorted_keys = sorted(keys, key=lambda x: (len(x), x))
            for key in sorted_keys:
                for equipment in equipment_pool_temp[key]:
                    equ.equipment.equipment_pool[equ.equipment.FREE].append(equipment)
            Log.log_debug_1(f"equipment updated")

            # for i, equipment in enumerate(equ.equipment.equipment_pool[equ.equipment.FREE]):
            #    if i %10 == 0:
            #        Log.log_debug(f'Page {i // 10 + 1}')
            #    Log.log_debug(f'{i}: {equipment.name} {equipment.stars} (Production id: {equipment.production_id}, Model id: {equipment.model_id}), category id: {equipment.category}')

        except KeyError:
            Log.log_debug_1("No provisional equipment data found in API response")

    def _filter_equipment(self, equipment_data: list):
        """Filter equipment based on ignore_equipment.json
        This is a workaround to ignore certain equipment from being processed,
        due to Kancolle API providing ghost equipment entries that do not exist in the game.
        See [record on Github](https://github.com/XVs32/kcauto_custom/discussions/123#discussioncomment-13599782) for more details.
        args:
            equipment_data (list): List of equipment data from API, ex.[{"api_id": 1, "api_slotitem_id": 33, "api_locked": 0, "api_level": 0},...]
        returns:
            filtered_equipment_data (list): List of equipment data after filtering
        """

        try:
            ignore_equipment_data = JsonData.load_json(
                "data|equipment|ignore_equipment.json"
            )
        except FileNotFoundError:
            ignore_equipment_data = {"equipment_production_id": []}
            JsonData.dump_json(
                ignore_equipment_data, "data|equipment|ignore_equipment.json"
            )
        ignored_equipment_production_id = ignore_equipment_data[
            "equipment_production_id"
        ]

        for i in range(len(equipment_data) - 1, -1, -1):
            if equipment_data[i]["api_id"] in ignored_equipment_production_id:
                Log.log_debug_1(
                    f"Ignoring equipment with production id {equipment_data[i]['api_id']}"
                )
                equipment_data.pop(i)

        return equipment_data

    def _process_map_info_json(self, data):

        filename = os.path.basename(data["url"])
        Log.log_debug_1(f"map info json received: {filename}")
        com.combat.gimmick_startup_judge(filename)

        return


api = ApiWrapper()
