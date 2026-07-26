import cv2
import numpy as np
import os
import glob
from pyquery import PyQuery
import PyChromeDevTools
from datetime import datetime, timedelta
from util.pyvisauto import Region, FindFailed, ImageMatch
from random import randint, uniform
from time import sleep

from quest.quest import Quest
import api.api_core as api
import args.args_core as arg
import config.config_core as cfg
import ships.ships_core as shp
from util.json_data import JsonData
import stats.stats_core as sts
from constants import (
    GAME_W,
    GAME_H,
    VISUAL_URL,
    API_URL,
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
from util.exceptions import ChromeCrashException
from util.logger import Log

import asyncio
from pyppeteer import connect


class Kca(object):
    """Primary kcauto utility class."""

    ASSETS_FOLDER = "assets"
    visual_tab_id = None
    visual_hook = None
    api_hook = None
    kc3_hook = None

    # See https://github.com/XVs32/kcauto_custom/issues/239 for coord system info
    viewport_x = None
    viewport_y = None
    game_x = None
    game_y = None
    last_ui = None
    r = {}
    html = None
    kc3_id = None

    screenshot_log = [None, None, None, None, None]

    def __init__(self):
        if self.kc3_id == None:
            try:
                data = JsonData.load_json("data|config|kc3_id.json")
                self.kc3_id = data.get("id", "hkgmldnainaglpjngpajnnjfhpdjkohh")
            except FileNotFoundError:
                Log.log_warn("kc3_id.json not found, using default KC3 id.")
                self.kc3_id = "hkgmldnainaglpjngpajnnjfhpdjkohh"
        Log.log_debug_1("Kca module initialized.")

    def hook_chrome(self):
        """Method that initializes the necessary hooks to Chrome using
        PyChromeDevTools. The visual hook connects to the tab that actually
        contains the Kancolle HTML5 canvas, while the api hook connects to the
        tab that interacts with the Kancolle backend. The former is used for
        detecting refreshes and when using the Chrome driver interaction mode,
        while the latter is used for reading all API interactions.

        Args:

        Raises:
            Exception: could not find Kancolle tabs in Chrome.
        """
        Log.log_msg("Hooking into Chrome.")
        self.cdt_init(target="api")
        self.cdt_init(target="visual")

        visual_tab = None
        visual_tab_id = None
        api_tab = None
        api_tab_id = None
        for n, tab in enumerate(self.visual_hook.tabs):
            if VISUAL_URL == tab["url"]:
                visual_tab = n
                visual_tab_id = tab["id"]
                self.visual_tab_id = visual_tab_id
            if API_URL in tab["url"]:
                api_tab = n
                api_tab_id = tab["id"]

        if visual_tab_id is None or api_tab_id is None:
            Log.log_error(
                "No Kantai Collection tab found in Chrome. Shutting down kcauto."
            )
            raise Exception("No running Kantai Collection tab found in Chrome.")

        self.visual_hook.connect_targetID(visual_tab_id)

        Log.log_debug_1(f"Connected to visual tab ({visual_tab}:{visual_tab_id})")
        self.visual_hook.Page.enable()

        self.api_hook.connect_targetID(api_tab_id)
        self.api_hook.Network.enable()
        Log.log_debug_1(f"Connected to API tab ({api_tab}:{api_tab_id})")
        Log.log_success("Connected to Chrome")

        coordinate_system.coor.find_game_window_offset()

    def hook_health_check(self):
        """Method that runs through the different events reported to the api
        and visual hooks to ascertain whether or not the tab has crashed or
        was refreshed.

        Raises:
            ChromeCrashException: Chrome tab crash was detected.
        """
        api_events = self.api_hook.pop_messages()
        visual_events = self.visual_hook.pop_messages()
        for event in api_events:
            if event["method"] == "Inspector.detached":
                Log.log_warn("Chrome API hook is stale. Reconnecting.")
                self.hook_chrome()
                return
        visual_events = self.visual_hook.pop_messages()
        for event in visual_events:
            if event["method"] == "Page.frameDetached":
                Log.log_warn("Chrome visual hook is stale. Reconnecting.")
                self.hook_chrome()
                return
            if event["method"] == "Inspector.targetCrashed":
                Log.log_warn("Chrome crash detected.")
                raise ChromeCrashException

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
        if cfg.config.general.interaction_mode is InteractionModeEnum.DIRECT_CONTROL:
            r.hover()
        elif cfg.config.general.interaction_mode is InteractionModeEnum.CHROME_DRIVER:
            self._chrome_driver_hover_method(r)

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
        if cfg.config.general.interaction_mode is InteractionModeEnum.DIRECT_CONTROL:
            corners = [
                r.x + pad[0],
                r.y + pad[1],
                r.x + r.w + pad[2],
                r.y + r.h + pad[3],
            ]
            if arg.args.parsed_args.debug_output:
                # Visit corners first
                r.hover(corners[0], corners[1])
                self.sleep(0.1)
                r.hover(corners[2], corners[1])
                self.sleep(0.1)
                r.hover(corners[0], corners[3])
                self.sleep(0.1)
                r.hover(corners[2], corners[3])
                self.sleep(0.1)

                # Draw debug with corners
            self._draw_debug_visualization(corners, arg.args.parsed_args.debug_output)

            r.click(pad=pad)
        elif cfg.config.general.interaction_mode is InteractionModeEnum.CHROME_DRIVER:
            self._chrome_driver_click_method(r, pad)

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
        if cfg.config.general.interaction_mode is InteractionModeEnum.DIRECT_CONTROL:
            corners = [
                r.x + pad[0],
                r.y + pad[1],
                r.x + r.w + pad[2],
                r.y + r.h + pad[3],
            ]
            if arg.args.parsed_args.debug_output:
                # Visit corners first
                r.hover(corners[0], corners[1])
                self.sleep(0.1)
                r.hover(corners[2], corners[1])
                self.sleep(0.1)
                r.hover(corners[0], corners[3])
                self.sleep(0.1)
                r.hover(corners[2], corners[3])
                self.sleep(0.1)

                # Draw debug with corners
            self._draw_debug_visualization(
                corners,
                arg.args.parsed_args.debug_output,
                border_color=(0, 0, 255),
                action=ActionEnum.SCROLL,
            )

            r.scroll(pad=pad, direction=direction, amount=amount)
        elif cfg.config.general.interaction_mode is InteractionModeEnum.CHROME_DRIVER:
            self._chrome_driver_scroll_method(r, pad, direction, amount)

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
        if cfg.config.general.interaction_mode is InteractionModeEnum.DIRECT_CONTROL:
            r_a.hover()
            self.sleep()
            r_b.drag(pad=pad)

        elif cfg.config.general.interaction_mode is InteractionModeEnum.CHROME_DRIVER:
            self._chrome_driver_drag_method(r_a, pad, r_b, pad)

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

        if self.game_x is None or self.game_y is None:
            return
        screen = Region(self.game_x, self.game_y, GAME_W, GAME_H)
        screen = screen.capture()
        screen = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

        cv2.rectangle(
            screen,
            (
                int(corners[0] - self.game_x),
                int(corners[1] - self.game_y),
            ),  # Top-left point
            (
                int(corners[2] - self.game_x),
                int(corners[3] - self.game_y),
            ),  # Bottom-right point
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
            self.r["shipgirl"].click()
            api.api.update_from_api({KCSAPIEnum.PORT})
            sts.stats.expedition.expeditions_received += 1
            self.wait("lower_right_corner", "global|next.png", 20)
            while self.exists("lower_right_corner", "global|next.png"):
                self.sleep()
                self.r["shipgirl"].click()
                self.r["top"].hover()
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

    def _override_hover_method(self, r, x, y):
        """Hover method override used when using Chrome Driver interaction
        mode.
        Args:
            r (Region, Match): Region/Match region to click
            x (int): x-coordinate of click generated by pyvisauto
            y (int): y-coordinate of click generated by pyvisauto
        """
        self._chrome_driver_hover_method(r)

    def _override_click_method(self, r, x, y, pad):
        """Click method override used when using Chrome Driver interaction
        mode.

        Args:
            r (Region, Match): Region/Match region to click
            x (int): x-coordinate of click generated by pyvisauto
            y (int): y-coordinate of click generated by pyvisauto
            pad (tuple): padding parameter used to modify click coordinate
        """
        self._chrome_driver_click_method(r, pad)

    def _override_scroll_method(self, r, x, y, pad, direction, amount):
        """Scroll method override used when using Chrome Driver interaction
        mode.

        Args:
            r (Region, Match): Region/Match region to scroll
            x (int): x-coordinate of scroll generated by pyvisauto
            y (int): y-coordinate of scroll generated by pyvisauto
            pad (tuple): padding parameter used to modify scroll coordinate
            direction (ScrollDirectionEnum): Scroll direction.
            amount (int): Number of scroll steps to perform.
        """
        self._chrome_driver_scroll_method(r, pad, direction, amount)

    def _chrome_driver_click_method(self, r, pad):
        """Click method used in Chrome Driver interaction mode.

        Args:
            r (Region, Match): Region/Match region to click
            pad (tuple): padding parameter used to modify click coordinate
        """

        offset_x = randint(pad[0], r.w + pad[2])
        offset_y = randint(pad[1], r.h + pad[3])
        x = r.x - self.viewport_x
        y = r.y - self.viewport_y

        # Draw debug visualization

        corners = [
            r.x + pad[0],  # Top-left corner
            r.y + pad[1],
            r.x + r.w + pad[2],
            r.y + r.h + pad[3],
        ]

        self._draw_debug_visualization(corners, arg.args.parsed_args.debug_output)

        # self.visual_hook.Input.synthesizeTapGesture(x= x + offset_x , y=y + offset_y)
        self.visual_hook.Input.dispatchMouseEvent(
            type="mouseMoved", x=x + offset_x, y=y + offset_y
        )
        self.sleep()
        self.visual_hook.Input.dispatchMouseEvent(
            type="mousePressed",
            x=x + offset_x,
            y=y + offset_y,
            clickCount=1,
            button="left",
        )
        self.sleep(0.1, 0.2)
        self.visual_hook.Input.dispatchMouseEvent(
            type="mouseReleased",
            x=x + offset_x,
            y=y + offset_y,
            clickCount=1,
            button="left",
        )
        self.sleep()

    def _chrome_driver_scroll_method(self, r, pad, direction, amount=1):
        """Scroll method used in Chrome Driver interaction mode.

        Args:
            r (Region, Match): Region/Match region to scroll
            pad (tuple): padding parameter used to modify scroll coordinate
            direction (ScrollDirectionEnum): Scroll direction.
            amount (int, optional): Number of scroll steps to perform.
        """

        offset_x = randint(pad[0], r.w + pad[2])
        offset_y = randint(pad[1], r.h + pad[3])
        x = r.x - self.viewport_x
        y = r.y - self.viewport_y

        # Draw debug visualization

        corners = [
            r.x + pad[0],  # Top-left corner
            r.y + pad[1],
            r.x + r.w + pad[2],
            r.y + r.h + pad[3],
        ]

        self._draw_debug_visualization(
            corners,
            arg.args.parsed_args.debug_output,
            border_color=(0, 0, 255),
            action=ActionEnum.SCROLL,
        )

        self.visual_hook.Input.dispatchMouseEvent(
            type="mouseMoved", x=x + offset_x, y=y + offset_y
        )
        self.sleep()

        if amount < 1:
            raise ValueError(f"Unsupported scroll amount: {amount}")

        if direction is ScrollDirectionEnum.UP:
            delta_y = -120
        elif direction is ScrollDirectionEnum.DOWN:
            delta_y = 120
        else:
            raise ValueError(f"Unsupported scroll direction: {direction}")

        for _ in range(amount):
            self.visual_hook.Input.dispatchMouseEvent(
                type="mouseWheel",
                x=x + offset_x,
                y=y + offset_y,
                deltaX=0,
                deltaY=delta_y,
            )
            self.sleep()

    def _chrome_driver_drag_method(self, r_a, pad_a, r_b, pad_b):
        """Click method used in Chrome Driver interaction mode.

        Args:
            r (Region, Match): Region/Match region to click
            pad (tuple): padding parameter used to modify click coordinate
        """

        offset_x = randint(-pad_a[3], r_a.w + pad_a[1])
        offset_y = randint(-pad_a[0], r_a.h + pad_a[2])
        x = r_a.x - self.viewport_x
        y = r_a.y - self.viewport_y

        self.visual_hook.Input.dispatchMouseEvent(
            type="mouseMoved", x=x + offset_x, y=y + offset_y
        )
        self.sleep()
        self.visual_hook.Input.dispatchMouseEvent(
            type="mousePressed",
            x=x + offset_x,
            y=y + offset_y,
            clickCount=1,
            button="left",
        )
        self.sleep()

        offset_x = randint(-pad_b[3], r_b.w + pad_b[1])
        offset_y = randint(-pad_b[0], r_b.h + pad_b[2])
        x = r_b.x - self.viewport_x
        y = r_b.y - self.viewport_y

        self.visual_hook.Input.dispatchMouseEvent(
            type="mouseMoved", x=x + offset_x, y=y + offset_y
        )
        self.sleep()
        self.visual_hook.Input.dispatchMouseEvent(
            type="mouseReleased",
            x=x + offset_x,
            y=y + offset_y,
            clickCount=1,
            button="left",
        )
        self.sleep()

    def _chrome_driver_hover_method(self, r):
        """hover method used in Chrome Driver interaction mode.

        Args:
            r (Region, Match): Region/Match region to hover
        """

        offset_x = randint(0, r.w)
        offset_y = randint(0, r.h)
        x = r.x - self.viewport_x
        y = r.y - self.viewport_y

        self.visual_hook.Input.dispatchMouseEvent(
            type="mouseMoved", x=x + offset_x, y=y + offset_y
        )

    def cdt_init(self, host="localhost", target="visual"):
        """method to hook this python program to chrome browser, cdt stands for ChromeDevTools

        Args:
            host (str, optional): Chrome dev protocol server address. Defaults
                to "localhost".
            port (int, optional): Chrome dev protocol server port. Defaults to
                9222.
            api (bool): api hook or not(default True)
        """

        port = cfg.config.general.chrome_dev_port
        chrome = PyChromeDevTools.ChromeInterface(host="localhost", port=port)
        if target == "api":
            self.api_hook = PyChromeDevTools.ChromeInterface(host=host, port=port)
        elif target == "visual":
            self.visual_hook = PyChromeDevTools.ChromeInterface(host=host, port=port)
        elif target == "kc3":
            self.kc3_hook = PyChromeDevTools.ChromeInterface(host=host, port=port)
        else:
            raise ValueError("Hook target must be either api, visual or kc3.")

        return

    async def get_html(self, url):

        port = cfg.config.general.chrome_dev_port
        # Connect to the Chrome browser
        browser = await connect(browserURL="http://localhost:" + str(port))

        # Create a new background tab
        page = await browser.newPage()

        # Navigate the background tab to a desired URL
        await page.goto(url)

        # Retrieve the HTML content
        self.html = await page.content()
        # Log.log_debug(f"kca.html: {self.html}")

        # Close the background tab
        await page.close()

        # Close the connection to the browser
        await browser.disconnect()

    def reload_kc3_strategy_page(self, subpage=""):
        """method to open/refresh the kc3 strategy page in chrome

        Args:
            subpage (string): The name of sub page to open. (ex. flowchart)
        """
        try:
            asyncio.get_event_loop().run_until_complete(
                self.get_html(
                    f"chrome-extension://{self.kc3_id}/pages/strategy/strategy.html{subpage}"
                )
            )
            # Wait for quest panel finish closing
            coordinate_system.coor.find_kancolle()
        except Exception as e:
            Log.log_warn(f"KC3 strategy page unavailable: {e}")
            self.html = None

        return

    def get_quest_dom(self):
        """method to get the raw quest info form KC3.

        Return:
            raw html text of KC3 quest page
        """

        import quest.quest_core as qst

        if qst.quest.is_quest_dom_cache_dirty == False:
            return qst.quest._quest_dom_cache

        self.reload_kc3_strategy_page(subpage="#flowchart")

        if self.html is None:
            Log.log_warn(
                "KC3 unavailable; quest DOM cache not updated, falling back to config defaults."
            )
            return None

        dom = PyQuery(self.html, parser="html")

        qst.quest._quest_dom_cache = dom("ul#questBox_rootFlow.questTree")
        # Log.log_debug(f"kac.quest_tree_dom:{quest_tree_dom}")
        qst.quest.is_quest_dom_cache_dirty = False

        return qst.quest._quest_dom_cache

    def get_quest_count(self, target_quest: Quest) -> dict[MapEnum, int] | None:
        """method to get the remaining action needed for the specified quest.
            For example, the remaining sorties needed for quest Bm3 could be {1-4:1, 3-5:0}

        Args:
            target_quest (Quest): The quest to check, in the form of Quest object.

        Return:
            dict with key of quest name, and value of remaining actions needed.
            return None if quest is not combat type, KC3 is unavailable, or quest count cannot be read.
        """

        target_quest_name = target_quest.name

        quest_tree_dom = self.get_quest_dom()

        if quest_tree_dom is None:
            Log.log_warn(
                f"KC3 unavailable; cannot get quest count for {target_quest_name}, using config defaults."
            )
            return None

        i = 0
        while True:
            quest_name = quest_tree_dom("div.questInfo").eq(i)(".questIcon").text()
            # Log.log_debug(f"quest_name:{quest_name}")

            if quest_name == target_quest_name:
                action_raw = (
                    quest_tree_dom("div.questInfo").eq(i)(".questCount").attr("title")
                )
                Log.log_debug_1(f"action_raw:{action_raw}")
                if action_raw == None:
                    return None
                action_raw_line = action_raw.split("\n")
                action = {}

                if quest_name == "Bw1":
                    action_raw_line[3] = action_raw_line[3].replace(" ", "/")
                    s_count = int(action_raw_line[3].split("/")[1]) - int(
                        action_raw_line[3].split("/")[0]
                    )
                    action_raw_line[2] = action_raw_line[2].replace(" ", "/")
                    boss_win_count = int(action_raw_line[2].split("/")[1]) - int(
                        action_raw_line[2].split("/")[0]
                    )
                    action_raw_line[1] = action_raw_line[1].replace(" ", "/")
                    boss_count = int(action_raw_line[1].split("/")[1]) - int(
                        action_raw_line[1].split("/")[0]
                    )
                    action_raw_line[0] = action_raw_line[0].replace(" ", "/")
                    sortie_count = int(action_raw_line[0].split("/")[1]) - int(
                        action_raw_line[0].split("/")[0]
                    )

                    if s_count > 0:
                        action[MapEnum.W1_1] = s_count
                    elif boss_win_count > 0:
                        action[MapEnum.W1_5] = boss_win_count
                    elif boss_count > 0:
                        action[MapEnum.W1_5] = boss_count
                    elif sortie_count > 0:
                        action[MapEnum.W1_1] = sortie_count

                elif quest_name == "Bq8":
                    action_raw_line[0] = action_raw_line[0].replace(" ", "/")
                    s_1_5_count = int(action_raw_line[0].split("/")[1]) - int(
                        action_raw_line[0].split("/")[0]
                    )
                    action_raw_line[1] = action_raw_line[1].replace(" ", "/")
                    s_7_1_count = int(action_raw_line[1].split("/")[1]) - int(
                        action_raw_line[1].split("/")[0]
                    )
                    action_raw_line[2] = action_raw_line[2].replace(" ", "/")
                    s_7_2_G_count = int(action_raw_line[2].split("/")[1]) - int(
                        action_raw_line[2].split("/")[0]
                    )
                    action_raw_line[3] = action_raw_line[3].replace(" ", "/")
                    s_7_2_M_count = int(action_raw_line[3].split("/")[1]) - int(
                        action_raw_line[3].split("/")[0]
                    )

                    if s_1_5_count > 0:
                        action[MapEnum.W1_5] = s_1_5_count
                    elif s_7_1_count > 0:
                        action[MapEnum.W7_1] = s_7_1_count
                    elif s_7_2_G_count > 0:
                        action[MapEnum.W7_2_G] = s_7_2_G_count
                    elif s_7_2_M_count > 0:
                        action[MapEnum.W7_2_M] = s_7_2_M_count

                elif quest_name[0] == "D":
                    for line in action_raw_line:
                        line = line.replace(" ", "/")
                        count = int(line.split("/")[1]) - int(line.split("/")[0])
                        import expedition.expedition_core as exp

                        map = exp.expedition.get_exp_enum_from_name(line.split("/")[-1])
                        if count > 0:
                            action[map] = count
                else:
                    for line in action_raw_line:
                        line = line.replace(" ", "/")
                        count = int(line.split("/")[1]) - int(line.split("/")[0])
                        line = line.replace("]", "[")
                        map = line.split("[")[1][1:]
                        if count > 0:
                            if MapEnum("B-" + map).without_quest_enum == MapEnum.W1_6_N:
                                # patch to turn B1-6-N from quest to B1-6
                                action[MapEnum.W1_6] = count
                            else:
                                action[MapEnum("B-" + map).without_quest_enum] = count

                return action
            elif quest_name == "":
                return None
            i = i + 1

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


kca = Kca()
