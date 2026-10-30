import cv2
import numpy as np
import os
import glob
from datetime import datetime, timedelta
from util.pyvisauto import Region, FindFailed, ImageMatch
from random import randint, uniform
from time import sleep

from quest.quest import Quest
import api.api_core as api
import api.api_listener as api_listener
import args.args_core as arg
import config.config_core as cfg
import factory.factory_core as fty
import ships.ships_core as shp
import stats.stats_core as sts
from util.json_data import JsonData
from constants import (
    GAME_W,
    GAME_H,
    API_URL,
    POI_URL_POSTFIX,
    EXACT,
    DEFAULT,
    SLEEP_MODIFIER,
)
from kca_enums.interaction_modes import InteractionModeEnum
from kca_enums.actions import ActionEnum
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.maps import MapEnum
from kca_enums.scroll_directions import ScrollDirectionEnum

import util.coordinate_system as coordinate_system
import util.click_tracker as clt
from util.exceptions import ChromeCrashException
from util.logger import Log
from util.poi_client import PoiClientError
from util.interaction_backend import InteractionBackend

import asyncio
from pyppeteer import connect


class Kca(object):
    """Primary kcauto utility class."""

    ASSETS_FOLDER = "assets"
    html = None

    screenshot_log = [None, None, None, None, None]

    @property
    def r(self):
        return coordinate_system.coor.r

    @property
    def last_ui(self):
        return coordinate_system.coor.last_ui

    @last_ui.setter
    def last_ui(self, value):
        coordinate_system.coor.last_ui = value

    @property
    def game_x(self):
        return coordinate_system.coor.game_x

    @property
    def game_y(self):
        return coordinate_system.coor.game_y

    # CDP / POI handles live in the active driver; these stay for callers that
    # still read them off kca.
    @property
    def api_hook(self):
        return getattr(self.interaction.driver, "api_hook", None)

    @property
    def poi_hook(self):
        return getattr(self.interaction.driver, "poi_hook", None)

    @property
    def poi_client(self):
        return getattr(self.interaction.driver, "poi_client", None)

    def __init__(self):
        self.interaction = InteractionBackend(self)
        Log.log_debug_1("Kca module initialized.")

    def hook_chrome(self):
        """Connect the active interaction driver (Chrome CDP hooks for direct
        control / Chrome driver, the loopback service for POI)."""
        return self.interaction.connect()

    # Kept as an alias for older call sites.
    hook_poi = hook_chrome

    def hook_health_check(self):
        """Ask the active driver whether its connection is still alive and
        reconnect when it is stale.

        Raises:
            ChromeCrashException: Chrome tab crash was detected.
        """
        driver = self.interaction.driver
        try:
            healthy = self.interaction.health_check()
        except (OSError, PoiClientError):
            healthy = False
        if not healthy:
            Log.log_warn(f"{driver.name} hook is stale. Reconnecting.")
            self.hook_chrome()

    def find_kancolle(self):
        """Method that finds the Kancolle game on-screen and determine the UI
        being used as well as the position of the game. On first startup the
        method will look for all UIs until one is found; on subsequent runs
        it will first look for the last found UI. Generates or modifies
        pre-defined regions accordingly.

        Where the game origin lives (desktop offset, browser viewport, or the
        POI frame) is decided by the interaction driver, not here.

        Raises:
            FindFailed: could not find the game on-screen.
        """
        Log.log_msg("Finding kancolle.")
        ref_r = None
        attempt = 0
        whole_screen_region = self.interaction.full_region()

        # look for last-seen UI, if set
        if self.last_ui:
            try:
                ref_r = self.find(
                    whole_screen_region,
                    f"global|kc_ref_point_{self.last_ui}.png",
                    EXACT,
                )
            except FindFailed:
                self.last_ui = None
                Log.log_debug_1("Last known UI not found.")

        # if last-seen UI was not found, or if kcauto is in first start
        while not ref_r:
            try:
                ref_r = self.find(
                    whole_screen_region, "global|kc_ref_point_1.png", EXACT
                )
                self.last_ui = 1
                Log.log_debug_1("Using UI 1 or 2")
                break
            except FindFailed:
                Log.log_debug_1("Not using UI 1 or 2")
            try:
                ref_r = self.find(
                    whole_screen_region, "global|kc_ref_point_2.png", EXACT
                )
                self.last_ui = 2
                Log.log_debug_1("Using UI 3")
                break
            except FindFailed:
                Log.log_debug_1("Not using UI 3")
            try:
                ref_r = self.find(
                    whole_screen_region, "global|kc_ref_point_3.png", EXACT
                )
                self.last_ui = 3
                Log.log_debug_1("Using UI 4 or 5")
                break
            except FindFailed:
                Log.log_debug_1("Not using UI 4 or 5")
            attempt += 1
            self.sleep(1)
            if attempt > 3:
                Log.log_error("Could not find Kancolle reference point.")
                raise FindFailed()

        new_game_x, new_game_y = self.interaction.resolve_game_origin(ref_r)
        Log.log_debug_1(f"Game X:{new_game_x}, Y:{new_game_y}")

        # click tracking is attached to the single backend entry
        if not arg.args.parsed_args.no_click_track:
            self.interaction.click_callback = clt.click_tracker.track_click

        if (
            new_game_x != coordinate_system.coor.game_x
            or new_game_y != coordinate_system.coor.game_y
        ):
            if (
                coordinate_system.coor.game_x is None
                or coordinate_system.coor.game_y is None
            ):
                Log.log_success("Game found. Initializing regions.")
            else:
                Log.log_msg("Game has moved.")
            coordinate_system.coor.game_x = new_game_x
            coordinate_system.coor.game_y = new_game_y
            coordinate_system.coor._update_regions()

        self.interaction.on_game_located()

        return True

    def start_kancolle(self):
        """Method that attempts to start Kancolle from the game's splash
        screen. If starting from the splash screen, kcauto will load the data
        from the get_data api call. Otherwise, it will load the stored data
        from previous startups.
        """

        # Create a pattern to match the files
        pattern = os.path.join(".", ".screenshot*.png")

        # Find all files that match the pattern
        files = glob.glob(pattern)

        # Remove all matching files
        for file in files:
            os.remove(file)

        screen = Region()
        if self.click_existing(screen, "global|game_start.png"):
            Log.log_msg("Starting kancolle from splash screen.")
            api.api.update_from_api(
                {KCSAPIEnum.GET_DATA, KCSAPIEnum.REQUIRE_INFO, KCSAPIEnum.PORT}
            )
            self.wait(screen, "nav|home_menu_sortie.png", 60)
            Log.log_success("Kancolle successfully started.")
            shp.ships.load_wctf_names(force_update=True)

        else:
            Log.log_debug_1("Can't find splash screen.")
            api.api.update_ship_library_from_json()

        return True

    def find_expedition_flag(self):
        flag = True

        # look for last-seen UI, if set
        if self.last_ui:
            if not self.exists(
                "upper_right", f"expedition|expedition_flag_{self.last_ui}.png"
            ):
                flag = False
        else:
            flag = False

        return flag

    def _create_asset_path(self, asset):
        """Helper method for generating the proper OS-safe path to an asset.

        Args:
            asset (str): kcauto-internal asset-style path. This should be in
                the format of '[folder1]|[folder2]|[imagename]'. 'folder1' is
                expected to be within the assets folder of kcauto.

        Returns:
            str: OS-safe path to an asset.
        """
        asset_split = asset.split("|")
        return os.path.join(self.ASSETS_FOLDER, *asset_split)

    def find(self, region, asset, similarity=DEFAULT, cached=False):
        """Wrapper method for finding an asset on-screen.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            asset (str): kcauto-style asset path.
            similarity (float, optional): minimum similarity score. Defaults to
                DEFAULT.
            cached (bool, optional): flag for using cached snapshot of region.
                Defaults to False.

        Returns:
            Match: Match instance of best asset match.
        """
        r = coordinate_system.coor.get_region(region)
        return r.find(self._create_asset_path(asset), similarity, cached)

    def find_all(self, region, asset, similarity=DEFAULT, cached=False):
        """Wrapper method for finding all matches of an asset on-screen.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            asset (str): kcauto-style asset path.
            similarity (float, optional): minimum similarity score. Defaults to
                DEFAULT.
            cached (bool, optional): flag for using cached snapshot of region.
                Defaults to False.

        Returns:
            [Match]: list of Match instances of asset matches above the defined
                similarity score.
        """
        r = coordinate_system.coor.get_region(region)
        return r.find_all(self._create_asset_path(asset), similarity, cached)

    def exists(self, region, asset, similarity=DEFAULT, cached=False):
        """Wrapper method for reporting whether an asset exists on-screen.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            asset (str): kcauto-style asset path.
            similarity (float, optional): minimum similarity score. Defaults to
                DEFAULT.
            cached (bool, optional): flag for using cached snapshot of region.
                Defaults to False.

        Returns:
            bool: True if asset exists on-screen, False otherwise.
        """
        r = coordinate_system.coor.get_region(region)
        return r.exists(self._create_asset_path(asset), similarity, cached)

    def wait(self, region, asset, wait=30, similarity=DEFAULT):
        """Wrapper method for waiting for an asset to exist on-screen.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            asset (str): kcauto-style asset path.
            wait (int): seconds to wait for asset to appear. Defaults to 30.
            similarity (float, optional): minimum similarity score. Defaults to
                DEFAULT.

        Returns:
            Match: Match instance of best asset match.
        """
        r = coordinate_system.coor.get_region(region)
        r.SCAN_RATE = 0.5  # slow down SCAN_RATE to 0.5 for lower CPU usage
        return r.wait(self._create_asset_path(asset), wait, similarity)

    def wait_vanish(self, region, asset, wait=30, similiarity=DEFAULT):
        """Wrapper method for waiting for an asset to no longer exist
        on-screen.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            asset (str): kcauto-style asset path.
            wait (int): seconds to wait for asset to disappear. Defaults to 30.
            similarity (float, optional): minimum similarity score. Defaults to
                DEFAULT.

        Returns:
            bool: True when asset no longer exists on-screen.
        """
        r = coordinate_system.coor.get_region(region)
        r.SCAN_RATE = 0.5  # slow down SCAN_RATE to 0.5 for lower CPU usage
        return r.wait_vanish(self._create_asset_path(asset), wait, similiarity)

    def hover(self, region):
        """Helper method that hovers the mouse cursor over the defined region.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
        """

        Log.log_debug_1(f"Hovering over region: {region}")

        self.sleep()

        r = coordinate_system.coor.get_region(region)
        self.interaction.hover(r)

        self.sleep()

    def click(self, region, pad=(0, 0, 0, 0)):
        """Helper method that clicks a passed in region. The pad parameter
        allows for further tweaking of the valid click region.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            pad (tuple, optional): click region modifier. Defaults to
                (0, 0, 0, 0) as offset of (X1, Y1, X2, Y2)
        """

        Log.log_debug_1(f"Clicking region: {region} with pad: {pad}")

        self.sleep()

        r = coordinate_system.coor.get_region(region)
        self.interaction.click(r, pad)

        self.sleep()

    def scroll(self, region, pad=(0, 0, 0, 0), *, direction, amount=1):
        """Helper method that scrolls a passed in region. The pad parameter
        allows for further tweaking of the valid scroll region.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            pad (tuple, optional): scroll region modifier. Defaults to
                (0, 0, 0, 0) as offset of (X1, Y1, X2, Y2)
            direction (ScrollDirectionEnum): scroll direction.
            amount (int, optional): Number of scroll steps to perform.
        """

        Log.log_debug_1(
            f"Scrolling region: {region} with pad: {pad}, direction: {direction}, amount: {amount}"
        )

        self.sleep()

        r = coordinate_system.coor.get_region(region)
        self.interaction.scroll(r, pad, direction, amount)

        self.sleep()

    def click_existing(
        self, region, asset, similarity=DEFAULT, pad=(0, 0, 0, 0), cached=False
    ):
        """Helper method that clicks a region if it exists. The pad parameter
        allows for further tweaking of the valid click region.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            asset (str): kcauto-style asset path.
            similarity (float, optional): minimum similarity score. Defaults to
                DEFAULT.
            pad (tuple, optional): click region modifier. Defaults to
                (0, 0, 0, 0).
            cached (bool, optional): flag for using cached snapshot of region.
                Defaults to False.

        Returns:
            bool: True if the region was found and clicked; False otherwise.
        """
        r = coordinate_system.coor.get_region(region)
        try:
            match = r.find(self._create_asset_path(asset), similarity, cached)
            self.click(match, pad=pad)
            return True
        except FindFailed:
            return False

    def wait_and_click(self, region, asset, wait=10, similarity=DEFAULT):
        """Helper method that waits for an asset match to show up in a region
        and then click it.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            asset (str): kcauto-style asset path.
            wait (int): seconds to wait for asset to appear. Defaults to 30.
            similarity (float, optional): minimum similarity score. Defaults to
                DEFAULT.
        """
        r = coordinate_system.coor.get_region(region)
        r.SCAN_RATE = 0.5  # slow down SCAN_RATE to 0.5 for lower CPU usage
        match = r.wait(self._create_asset_path(asset), wait, similarity)
        self.click(match)

    def drag(self, start_region, end_region, pad=(0, 0, 0, 0)):
        """Helper method that clicks a passed in region. The pad parameter
        allows for further tweaking of the valid click region.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
            pad (tuple, optional): click region modifier. Defaults to
                (0, 0, 0, 0).
        """

        Log.log_debug_1(
            f"Dragging from region: {start_region} to region: {end_region} with pad: {pad}"
        )

        self.sleep()

        r_a = coordinate_system.coor.get_region(start_region)
        r_b = coordinate_system.coor.get_region(end_region)
        self.interaction.drag(r_a, r_b, pad)

        self.sleep()

    def _draw_debug_visualization(
        self,
        corners,
        save_as_file,
        border_color=(0, 255, 0),
        action=ActionEnum.CLICK,
    ):
        """Draw debug visualization showing regions and click points

        Args:
            r (Region): Region to highlight
            click_x (int, optional): X coordinate of click point
            click_y (int, optional): Y coordinate of click point
            corners (list, optional): List of corner points visited
        """

        if (
            coordinate_system.coor.game_x is None
            or coordinate_system.coor.game_y is None
        ):
            return
        screen = Region(0, 0, GAME_W, GAME_H)
        screen = screen.capture()
        screen = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

        cv2.rectangle(
            screen,
            (int(corners[0]), int(corners[1])),
            (int(corners[2]), int(corners[3])),
            border_color,
            2,
        )

        Kca.screenshot_log.pop(0)
        Kca.screenshot_log.append(screen)

        if save_as_file:
            # Save debug image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # create folder if not exist
            if not os.path.exists("debug"):
                os.makedirs("debug")

            cv2.imwrite(f"debug/{action.value}_{timestamp}.png", screen)

    def sleep(self, base=None, flex=None):
        """Helper method for sleeping the script. Adds in random variance to
        the time slept. If no parameters are passed the sleep length will be
        between 0.3 and 0.7 seconds. The sleep time is further influenced by
        the SLEEP_MODIFIER.

        Args:
            base (int/float, optional): base number of seconds to sleep.
                Defaults to None.
            flex (int/float, optional): allowed amount of time to deviate from
                the base sleep length. Defaults to None.
        """
        if base is None:
            sleep(uniform(0.3, 0.7) + SLEEP_MODIFIER)
        else:
            flex = base if flex is None else flex
            sleep(uniform(base, base + flex) + SLEEP_MODIFIER)

    def receive_expedition(self):

        Log.log_debug_1("Starting to receive expedition.")

        received_expeditions = False
        while self.find_expedition_flag():
            Log.log_msg("Expedition received.")
            coordinate_system.coor.r["shipgirl"].click()
            api.api.update_from_api({KCSAPIEnum.PORT})
            sts.stats.expedition.expeditions_received += 1
            self.wait("lower_right_corner", "global|next.png", 20)
            while self.exists("lower_right_corner", "global|next.png"):
                self.sleep()
                coordinate_system.coor.r["shipgirl"].click()
                coordinate_system.coor.r["top"].hover()
                received_expeditions = True
                self.sleep()

            import quest.quest_core as qst

            qst.quest.is_quest_dom_cache_dirty = True

        return received_expeditions

    def while_wrapper(
        self, conditional_func, internal_func=None, timeout=None, attempt_limit=None
    ):
        """A wrapper for while conditionals that allow for execution timeouts
        and loop number limits to be defined. The conditional_func parameter
        should be a function or lambda with it returning True when the while
        loop should exit successfully. The internal_function, if specified,
        will execute within the while loop. Either timeout or attempt_limit
        must be specified. Meant to facilitate visual asset searches in while
        loops.

        Args:
            conditional_func (func/lambda): conditional function/lambda.
            internal_func (func/lambda): function/lambda to execute within
                the while loop. Defaults to None.
            timeout (int, optional): max number of seconds the while loop
                should execute. Defaults to None.
            attempt_limit (int, optional): max number of times the while loop
                should execute. Defaults to None.

        Raises:
            TypeError: neither timeout or attempt limit specified.
            FindFailed: the conditional failed to succeed before the timeout
                or within the attempt limit.

        Returns:
            True: conditional_func succeeded and returned True
        """
        if not timeout and not attempt_limit:
            raise TypeError("timeout or attempt_limit must be defined.")

        failed_conditional = False
        if timeout:
            end_time = datetime.now() + timedelta(seconds=timeout)
        elif attempt_limit:
            counter = 0

        while not conditional_func():
            if timeout and datetime.now() > end_time:
                failed_conditional = True
                break
            elif attempt_limit:
                counter += 1
                if counter >= attempt_limit:
                    failed_conditional = True
                    break
            if internal_func:
                internal_func()

        if failed_conditional:
            raise FindFailed("Conditional failed by exceeding timeout or attempt limit")

        return True

    def readable_list_join(self, raw_list):
        """Helper method for joining a list into a human-readable string,
        adding 'and' between the second to last and last items as needed.

        Args:
            raw_list (list): list to join

        Returns:
            str: joined string
        """
        display_text = ", ".join([str(i) for i in raw_list])
        display_text = " and".join(display_text.rsplit(",", 1))
        return display_text

    def get_quest_count(self, target_quest: Quest) -> dict[MapEnum, int] | None:
        """method to get the remaining action needed for the specified quest.
            For example, the remaining sorties needed for quest Bm3 could be {1-4:1, 3-5:0}

        Args:
            target_quest (Quest): The quest to check, in the form of Quest object.

        Return:
            dict with key of quest name, and value of remaining actions needed.
            return None if quest is not combat type, poi is unavailable, or quest count cannot be read.
        """

        poi_quest_stats = self.get_poi_quest_stats()

        if not poi_quest_stats:
            Log.log_warn(
                f"poi API data unavailable; cannot get quest count for {target_quest.name}."
            )
            return None
        if poi_quest_stats.get("error"):
            Log.log_warn(
                f"poi quest stats error; cannot get quest count for "
                f"{target_quest.name}: {poi_quest_stats.get('error')}"
            )
            self._dump_poi_quest_stats_for_debug(poi_quest_stats, target_quest)
            return None

        quest_id = str(target_quest.quest_id)
        records = poi_quest_stats.get("records", {})

        if quest_id not in records:
            Log.log_debug_1(
                f"Quest {quest_id} ({target_quest.name}) is not currently tracked."
            )
            self._dump_poi_quest_stats_for_debug(poi_quest_stats, target_quest)
            return None

        quest_record = records[quest_id]
        action = {}

        def get_remaining(obj):
            if not isinstance(obj, dict):
                return 0
            return max(0, obj.get("required", 0) - obj.get("count", 0))

        for key, val in quest_record.items():
            if key == "id" or not isinstance(
                val, dict
            ):  # skip non-quest-requirements keys
                continue

            remaining = get_remaining(val)
            if remaining <= 0:
                continue

            if target_quest.category.is_expedition():
                import expedition.expedition_core as exp

                exp_name = val.get("description", None)

                if exp_name == None:
                    continue

                map_enum = exp.expedition.get_exp_enum_from_name(exp_name)
                if map_enum:
                    action[map_enum] = remaining
                else:
                    continue
            if target_quest.category.is_factory():
                if target_quest.is_factroy_development_quest():
                    action[fty.factory.DEVELOPMENT] = remaining
                elif target_quest.is_factroy_construction_quest():
                    action[fty.factory.CONSTRUCTION] = remaining
                else:
                    continue
            else:
                desc = val.get("description", "")  # fallback for sortie without @
                if "-" in desc:
                    try:
                        raw_num = desc.split(" ")[0]
                        mapped_enum = self.string_to_mapenum(raw_num)
                        if mapped_enum:
                            action[mapped_enum] = remaining
                    except Exception:
                        continue

        return action if action else None

    def _dump_poi_quest_stats_for_debug(self, poi_quest_stats, target_quest: Quest):
        if not (arg.args.parsed_args is not None and arg.args.parsed_args.debug_output):
            return

        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        dump_path = (
            f"debug|poi_quest_records_{target_quest.name}_{target_quest.quest_id}_"
            f"{timestamp}.json"
        )
        try:
            JsonData.dump_json(poi_quest_stats, dump_path, pretty=True)
            Log.log_debug_1(
                "Dumped POI quest stats for quest count debugging to "
                f"{JsonData.create_path(dump_path)}."
            )
        except Exception as e:
            Log.log_warn(f"Failed to dump POI quest stats for debugging: {e}")

    def string_to_mapenum(self, raw_num: str) -> MapEnum:
        """Converts raw poi map identifier strings (like '15', '16', '722', '732', '5-4')
        to the corresponding standardized MapEnum.

        Handles multi-phase map bosses (e.g., 7-2-G, 7-2-M, 7-3-E, 7-3-P).
        """
        if not raw_num:
            return None
        num = raw_num.strip()

        special_mappings = {
            "16": MapEnum.W1_6_N,
            "721": MapEnum.W7_2_G,
            "722": MapEnum.W7_2_M,
            "731": MapEnum.W7_3_E,
            "732": MapEnum.W7_3_P,
            "7-2-1": MapEnum.W7_2_G,
            "7-2-2": MapEnum.W7_2_M,
            "7-3-1": MapEnum.W7_3_E,
            "7-3-2": MapEnum.W7_3_P,
        }

        if num in special_mappings:
            return special_mappings[num]

        if "-" in num:
            map_str = f"B-{num}"

        elif num.isdigit() and len(num) == 2:
            map_str = f"B-{num[0]}-{num[1]}"

        else:
            Log.log_error(
                f"Unknown map string format found: {map_str} (Original input: {num})"
            )
            return None

        try:
            enum_item = MapEnum(map_str)
            return enum_item.without_quest_enum
        except (ValueError, KeyError):
            Log.log_warn(
                f"MapEnum not found for map string: {map_str} (Original input: {num})"
            )
            return None

    def get_poi_quest_stats(self):
        import json

        Log.log_debug_1("get poi quests stats...")

        if cfg.config.general.interaction_mode is InteractionModeEnum.POI:
            try:
                return self.poi_client.get_quest_stats()
            except PoiClientError as e:
                Log.log_error(f"Failed to get poi quests stats: {str(e)}")
                return {}

        js_code = """
        (() => {
            const diagnostics = () => {
                const interestingWindowKeys = [
                    "getStore",
                    "POI_VERSION"
                ].filter((key) => key in window);

                return {
                    url: window.location?.href,
                    title: document?.title,
                    interestingWindowKeys,
                    hasGetStore: typeof window.getStore,
                    hasPoi: typeof window.poi
                };
            };

            try {
                const store = window.getStore();
        
                if (store && store.info && store.info.quests) {
                    return JSON.stringify(store.info.quests);
                }
        
                return JSON.stringify({
                    error: "POI quest store not found",
                    diagnostics: diagnostics()
                });
            } catch (e) {
                return JSON.stringify({
                    error: e.message,
                    diagnostics: diagnostics()
                });
            }
        })()
        """

        try:
            response = self.poi_hook.Runtime.evaluate(
                expression=js_code, returnByValue=True
            )

            Log.log_debug_2(f"response: {response}")

            if isinstance(response, (list, tuple)) and len(response) > 0:
                resp_dict = response[0]
            else:
                resp_dict = response

            if resp_dict and "result" in resp_dict and "result" in resp_dict["result"]:
                raw_json = resp_dict["result"]["result"].get("value", "{}")
                poi_quests = json.loads(raw_json)
                return poi_quests
            else:
                Log.log_error("Failed to parse CDP response data structure from poi.")
                return {}

        except Exception as e:
            Log.log_error(f"Failed to get poi quests stats: {str(e)}")
            return {}

    def save_screenshots(self):

        import shutil

        # Directory to store crash screenshots
        SAVE_DIR = "crash_screenshots"

        # Remove the directory from the previous run if it exists
        if os.path.exists(SAVE_DIR):
            print(f"Removing old screenshots directory: '{SAVE_DIR}'")
            shutil.rmtree(SAVE_DIR)
        # Create the directory if it doesn't exist
        os.makedirs(SAVE_DIR, exist_ok=True)

        print(f"Saving screenshots to '{SAVE_DIR}'...")

        for i, screen in enumerate(Kca.screenshot_log):
            file_path = os.path.join(SAVE_DIR, f"screenshot_{i}.png")
            try:
                cv2.imwrite(file_path, screen)
                print(f"Saved: {file_path}")
            except Exception as e:
                print(f"Failed to save screenshot {i}: {e}")

    def pause_if_configured(self, dialog=None):
        if cfg.config.combat.paused_after_fleetswitch:
            if dialog:
                Log.log_msg(dialog)
            Log.log_warn("Press Enter to continue")
            input()

    def close(self):
        """Release POI client and webhook resources during shutdown."""
        self.interaction.close()
        api_listener.api_listener.stop()


kca = Kca()
