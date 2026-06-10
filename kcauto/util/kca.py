import cv2
import numpy as np
import os
import glob
from sys import platform, exit
import requests
from pyquery import PyQuery
from sys import path_hooks
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
import util.click_tracker as clt
from util.json_data import JsonData
import stats.stats_core as sts
from constants import (
    GAME_W, GAME_H, VISUAL_URL, STRATEGY_ROOM_URL, API_URL, EXACT, DEFAULT, SLEEP_MODIFIER)
from kca_enums.interaction_modes import InteractionModeEnum
from kca_enums.kcsapi_paths import KCSAPIEnum
from kca_enums.maps import MapEnum
from kca_enums.expeditions import ExpeditionEnum

from util.exceptions import ChromeCrashException
from util.logger import Log

import asyncio
from pyppeteer import connect

class Kca(object):
    """Primary kcauto utility class.
    """
    
    KC_REF_OFFSET = (-144, 0)
    BROWSER_REF_ENTROPY_THRESHOLD = 0.5
    BROWSER_REF_SIZE = 100
    
    ASSETS_FOLDER = 'assets'
    visual_tab_id = None
    visual_hook = None
    api_hook = None
    kc3_hook = None
    css_x = None
    css_y = None
    game_x = None
    game_y = None
    last_ui = None
    r = {}
    html = None
    kc3_id = None
    
    screenshot_log = [None, None, None, None, None]

    def __init__(self):
        if self.kc3_id ==None:
            try:
                data = JsonData.load_json('data|config|kc3_id.json')
                self.kc3_id = data.get('id', "hkgmldnainaglpjngpajnnjfhpdjkohh")
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
            if VISUAL_URL == tab['url']:
                visual_tab = n
                visual_tab_id = tab['id']
                self.visual_tab_id = visual_tab_id
            if API_URL in tab['url']:
                api_tab = n
                api_tab_id = tab['id']

        if visual_tab_id is None or api_tab_id is None:
            Log.log_error(
                "No Kantai Collection tab found in Chrome. Shutting down "
                "kcauto.")
            raise Exception(
                "No running Kantai Collection tab found in Chrome.")

        self.visual_hook.connect_targetID(visual_tab_id)

        Log.log_debug_1(
            f"Connected to visual tab ({visual_tab}:{visual_tab_id})")
        self.visual_hook.Page.enable()

        self.api_hook.connect_targetID(api_tab_id)
        self.api_hook.Network.enable()
        Log.log_debug_1(f"Connected to API tab ({api_tab}:{api_tab_id})")
        Log.log_success("Connected to Chrome")
        
        self.find_game_window_offset()

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
            if event['method'] == 'Inspector.detached':
                Log.log_warn("Chrome API hook is stale. Reconnecting.")
                self.hook_chrome()
                return
        visual_events = self.visual_hook.pop_messages()
        for event in visual_events:
            if event['method'] == 'Page.frameDetached':
                Log.log_warn("Chrome visual hook is stale. Reconnecting.")
                self.hook_chrome()
                return
            if event['method'] == 'Inspector.targetCrashed':
                Log.log_warn("Chrome crash detected.")
                raise ChromeCrashException

    def start_kancolle(self):
        """Method that attempts to start Kancolle from the game's splash
        screen. If starting from the splash screen, kcauto will load the data
        from the get_data api call. Otherwise, it will load the stored data
        from previous startups.
        """
        
        # Create a pattern to match the files
        pattern = os.path.join('.', '.screenshot*.png')

        # Find all files that match the pattern
        files = glob.glob(pattern)

        # Remove all matching files
        for file in files:
            os.remove(file)

        screen = Region()
        if self.click_existing(screen, 'global|game_start.png'):
            Log.log_msg("Starting kancolle from splash screen.")
            api.api.update_from_api({
                KCSAPIEnum.GET_DATA, KCSAPIEnum.REQUIRE_INFO, KCSAPIEnum.PORT})
            self.wait(screen, 'nav|home_menu_sortie.png', 60)
            Log.log_success("Kancolle successfully started.")
            shp.ships.load_wctf_names(force_update=True)

        else:
            Log.log_debug_1("Can't find splash screen.")
            api.api.update_ship_library_from_json()

        return True

    def find_game_window_offset(self):
        """Method that finds the game window offset for chrome driver"""
        Log.log_msg("Finding browser offset")
        
        whole_screen_region = Region()
        Log.log_debug_1(f"whole_screen_region.x: {whole_screen_region.x}")
        Log.log_debug_1(f"whole_screen_region.y: {whole_screen_region.y}")
        Log.log_debug_1(f"whole_screen_region.w: {whole_screen_region.w}")
        Log.log_debug_1(f"whole_screen_region.h: {whole_screen_region.h}")
        
        retry = 0
        max_retries = 5
        retry_delay = 1
        
        import base64
        while retry < max_retries:
            try:
                whole_screen = whole_screen_region.capture()
                whole_screen_rgb = np.array(whole_screen)
                whole_screen_gray = cv2.cvtColor(whole_screen_rgb, cv2.COLOR_BGR2GRAY)

                screenshot_raw = self.visual_hook.Page.captureScreenshot()
                
                if screenshot_raw is None or not screenshot_raw:
                    raise ValueError("Failed to capture screenshot from Chrome")
                    
                if len(screenshot_raw) == 0 or "result" not in screenshot_raw[0]:
                    raise ValueError("Invalid screenshot data structure")
                    
                result = screenshot_raw[0]["result"]
                if "data" not in result:
                    raise ValueError("No image data in screenshot result")
                    
                screenshot_data = base64.b64decode(result['data'])
                screenshot_gray = cv2.imdecode(np.frombuffer(screenshot_data, np.uint8), cv2.IMREAD_GRAYSCALE)

                Log.log_debug_1(f"chrome driver browser size: {(screenshot_gray.shape[1], screenshot_gray.shape[0])}")

                window_width = min(GAME_W, screenshot_gray.shape[1])
                window_height = min(GAME_H, screenshot_gray.shape[0])
                ref_size = min(self.BROWSER_REF_SIZE, window_width, window_height)
                center_x = (window_width - ref_size) // 2
                center_y = (window_height - ref_size) // 2

                x_positions = self._build_sliding_positions(screenshot_gray.shape[1], window_width, GAME_W)
                y_positions = self._build_sliding_positions(screenshot_gray.shape[0], window_height, GAME_H)

                valid_ref_found = False

                for window_y in y_positions:
                    for window_x in x_positions:
                        slide_window = screenshot_gray[window_y:window_y + window_height, window_x:window_x + window_width]

                        ref = slide_window[center_y:center_y + ref_size, center_x:center_x + ref_size]

                        ref_entropy = self._calc_grayscale_entropy(ref)
                        Log.log_debug_1(f"ref entropy at window ({window_x}, {window_y}): {ref_entropy:.4f}")

                        if ref_entropy < self.BROWSER_REF_ENTROPY_THRESHOLD:
                            continue

                        valid_ref_found = True
                        start_x = window_x + center_x
                        start_y = window_y + center_y
                        if self._try_browser_offset_match(whole_screen_gray, ref, start_x, start_y):
                            return True

                if not valid_ref_found:
                    Log.log_warn("No valid reference clip found in sliding windows, falling back to full browser screenshot.")
                    if self._try_browser_offset_match(whole_screen_gray, screenshot_gray, 0, 0):
                        return True
                    raise ValueError("No valid sliding window reference found and full browser match failed")
                else:
                    raise ValueError("No browser offset found from valid references")
                
            except Exception as e:
                Log.log_error(f"Attempt {retry + 1}/{max_retries} failed: {str(e)}")
                retry += 1
                if retry < max_retries:
                    self.sleep(retry_delay)
                    continue
                else:
                    Log.log_error("Failed to find browser offset after max retries")
                    
                    if self.css_x is None or self.css_y is None:
                        Log.log_error("Browser offset not found. Please check your Chrome setup.")
                        exit(1)
                    
                    return False

    def _build_sliding_positions(self, full_size, window_size, step_size):
        """Build sliding window positions while ensuring the far edge is checked."""
        if full_size <= window_size:
            return [0]

        positions = list(range(0, full_size - window_size + 1, step_size))
        last_position = full_size - window_size
        if positions[-1] != last_position:
            positions.append(last_position)
        return positions

    def _try_browser_offset_match(self, whole_screen_gray, ref, start_x, start_y):
        """Try matching a browser reference image against the full screen."""
        match = cv2.matchTemplate(whole_screen_gray, ref, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
        Log.log_debug_1(f"start_x: {start_x}")
        Log.log_debug_1(f"start_y: {start_y}")
        Log.log_debug_1(f"max_loc: {max_loc}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not os.path.exists("debug"):
            os.makedirs("debug")

        cv2.imwrite(f"debug/browser_ref_clip_{timestamp}.png", ref)
        if max_val < 0.9:
            Log.log_error(f"Match value {max_val} is below threshold")
            return False

        self.css_x = max_loc[0] - start_x
        self.css_y = max_loc[1] - start_y
        Log.log_success(f"Browser offset found at X: {self.css_x}, Y: {self.css_y}")
        return True

    def _calc_grayscale_entropy(self, image):
        """Calculate Shannon entropy for a grayscale image."""
        hist = cv2.calcHist([image], [0], None, [256], [0, 256])
        total = float(hist.sum())
        if total == 0:
            return 0.0

        probabilities = hist / total
        probabilities = probabilities[probabilities > 0]
        return float(-np.sum(probabilities * np.log2(probabilities)))

    def find_kancolle(self):
        """Method that finds the Kancolle game on-screen and determine the UI
        being used as well as the position of the game. On first startup the
        method will look for all UIs until one is found; on subsequent runs
        it will first look for the last found UI. Generates or modifies
        pre-defined regions accordingly.

        Raises:
            FindFailed: could not find the game on-screen.
        """
        Log.log_msg("Finding kancolle.")
        ref_r = None
        attempt = 0
        screen = Region()

        # look for last-seen UI, if set
        if self.last_ui:
            try:
                ref_r = self.find(
                    screen, f'global|kc_ref_point_{self.last_ui}.png', EXACT)
            except FindFailed:
                self.last_ui = None
                Log.log_debug_1("Last known UI not found.")

        # if last-seen UI was not found, or if kcauto is in first start
        while not ref_r:
            try:
                ref_r = self.find(screen, 'global|kc_ref_point_1.png', EXACT)
                self.last_ui = 1
                Log.log_debug_1("Using UI 1 or 2")
                break
            except FindFailed:
                Log.log_debug_1("Not using UI 1 or 2")
            try:
                ref_r = self.find(screen, 'global|kc_ref_point_2.png', EXACT)
                self.last_ui = 2
                Log.log_debug_1("Using UI 3")
                break
            except FindFailed:
                Log.log_debug_1("Not using UI 3")
            try:
                ref_r = self.find(screen, 'global|kc_ref_point_3.png', EXACT)
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

        new_game_x = ref_r.x + self.KC_REF_OFFSET[0]
        new_game_y = ref_r.y + self.KC_REF_OFFSET[1]
        Log.log_debug_1(f"Game X:{new_game_x}, Y:{new_game_y}")

        # define click callback as needed
        if not arg.args.parsed_args.no_click_track:
            ImageMatch.click_callback = clt.click_tracker.track_click

        # define click and hover method overrides as needed
        if (cfg.config.general.interaction_mode
                is InteractionModeEnum.CHROME_DRIVER):
            ImageMatch.override_click_method = self._override_click_method
            ImageMatch.override_hover_method = self._override_hover_method

        if new_game_x != self.game_x or new_game_y != self.game_y:
            if not self.game_x or self.game_y:
                Log.log_success("Game found. Initializing regions.")
            else:
                Log.log_msg("Game has moved. Shifting regions.")
            self.game_x = new_game_x
            self.game_y = new_game_y
            self._update_regions()
            
        self.find_game_window_offset()

        return True

    def find_expedition_flag(self):
        flag = True

        # look for last-seen UI, if set
        if self.last_ui:
            if not self.exists('upper_right', f'expedition|expedition_flag_{self.last_ui}.png'):
                flag = False 
        else:
            flag = False 

        return flag

    def _update_regions(self):
        """Method that generates or updates all pre-defined regions
        accordingly based on the game's current x and y position.
        """
        Log.log_debug_1("Updating regions.")
        x = self.game_x
        y = self.game_y
        w = GAME_W
        h = GAME_H
        hw = w // 2
        hh = h // 2

        # general regions
        self._create_or_shift_region('kc', x, y, w, h)
        self._create_or_shift_region('left', x, y, hw, h)
        self._create_or_shift_region('right', x + hw, y, hw, h)
        self._create_or_shift_region('upper', x, y, w, hh)
        self._create_or_shift_region('lower', x, y + hh, w, hh)
        self._create_or_shift_region('upper_left', x, y, hw, hh)
        self._create_or_shift_region('upper_right', x + hw, y, hw, hh)
        self._create_or_shift_region('lower_left', x, y + hh, hw, hh)
        self._create_or_shift_region('lower_right', x + hw, y + hh, hw, hh)
        self._create_or_shift_region(
            'lower_right_corner', x + 1100, y + 620, 100, 100)
        self._create_or_shift_region('center', x + 225, y + 180, 750, 360)
        self._create_or_shift_region('top', x + 400, y + 12, 800, 30)
        self._create_or_shift_region('shipgirl', x + 700, y + 130, 400, 420)
        self._create_or_shift_region(
            'combat_click', x + 700, y + 680, 200, 30)
        # function-specific regions
        self._create_or_shift_region(
            'expedition_flag', x + 750, y + 20, 70, 50)
        self._create_or_shift_region('top_menu', x + 185, y + 50, 800, 50)
        self._create_or_shift_region(
            'top_menu_quest', x + 790, y + 50, 105, 45)
        self._create_or_shift_region('home_menu', x + 45, y + 130, 500, 490)
        self._create_or_shift_region('side_menu', x, y + 190, 145, 400)
        self._create_or_shift_region(
            'top_submenu', x + 145, y + 145, 1055, 70)
        self._create_or_shift_region(
            'quest_status', x + 1065, y + 165, 95, 500)
        self._create_or_shift_region(
            'check_damage_combat', x + 470, y + 215, 50, 475)
        self._create_or_shift_region('lbas', x + 500, y + 5, 200, 45)
        self._create_or_shift_region(
            'lbas_mode_switch', x + 1135, y + 200, 55, 80)
        self._create_or_shift_region('7th_next', x + 386, y + 400, 27, 27)
        # combat-related regions
        self._create_or_shift_region('c_world', x + 180, y + 635, 650, 65)
        self._create_or_shift_region(
            'formation_line_ahead', x + 596, y + 256, 250, 44)
        self._create_or_shift_region(
            'formation_double_line', x + 791, y + 256, 250, 44)
        self._create_or_shift_region(
            'formation_diamond', x + 989, y + 256, 150, 44)
        self._create_or_shift_region(
            'formation_echelon', x + 596, y + 495, 252, 44)
        self._create_or_shift_region(
            'formation_line_abreast', x + 791, y + 495, 253, 44)
        self._create_or_shift_region(
            'formation_vanguard', x + 989, y + 495, 150, 44)
        self._create_or_shift_region(
            'formation_combined_fleet_1', x + 640, y + 240, 215, 45)
        self._create_or_shift_region(
            'formation_combined_fleet_2', x + 890, y + 240, 215, 45)
        self._create_or_shift_region(
            'formation_combined_fleet_3', x + 640, y + 445, 215, 45)
        self._create_or_shift_region(
            'formation_combined_fleet_4', x + 890, y + 445, 215, 45)
        # factory-related regions
        self._create_or_shift_region(
            "build_slot_1_stat_region", x + 595, y + 180, 150, 60)
        self._create_or_shift_region(
            "build_slot_2_stat_region", x + 595, y + 305, 150, 60)
        self._create_or_shift_region(
            "build_slot_1_region", x + 900, y + 260, 60, 15)
        self._create_or_shift_region(
            "build_slot_2_region", x + 900, y + 380, 60, 15)
        self._create_or_shift_region(
            "order_confirm_region", x + 975, y + 635, 200, 50)
        self._create_or_shift_region(
            "use_item_region", x + 635, y + 580, 100, 20)
        self._create_or_shift_region(
            "develop_region", x + 215, y + 480, 200, 50)
        self._create_or_shift_region(
            "order_oil_region_1", x + 552, y + 226, 10, 10)
        self._create_or_shift_region(
            "order_oil_region_10", x + 742, y + 194, 10, 10)
        self._create_or_shift_region(
            "order_oil_region_100", x + 742, y + 236, 10, 10)
        self._create_or_shift_region(
            "order_ammo_region_1", x + 552, y + 420, 10, 10)
        self._create_or_shift_region(
            "order_ammo_region_10", x + 742, y + 390, 10, 10)
        self._create_or_shift_region(
            "order_ammo_region_100", x + 742, y + 430, 10, 10)
        self._create_or_shift_region(
            "order_steel_region_1", x + 890, y + 226, 10, 10)
        self._create_or_shift_region(
            "order_steel_region_10", x + 1085, y + 194, 10, 10)
        self._create_or_shift_region(
            "order_steel_region_100", x + 1085, y + 236, 10, 10) 
        self._create_or_shift_region(
            "order_bauxite_region_1", x + 890, y + 420, 10, 10)
        self._create_or_shift_region(
            "order_bauxite_region_10", x + 1085, y + 390, 10, 10)
        self._create_or_shift_region(
            "order_bauxite_region_100", x + 1085, y + 430, 10, 10)

        # expedition-related regions
        self._create_or_shift_region(
            "expedition_scoll_down_mark", x + 420, y + 600, 70, 20)
        self._create_or_shift_region(
            "expedition_scoll_down", x + 440, y + 610, 20, 20)
        
        self._create_or_shift_region(
            "expedition_scoll_up", x + 440, y + 200, 20, 20)
        
        # equipment-related regions
        self._create_or_shift_region('equipment_panel', x + 455, y + 226, 125, 268)
        self._create_or_shift_region('ship_1', x + 210, y + 228, 230, 47)
        self._create_or_shift_region('ship_2', x + 210, y + 309, 230, 47)
        self._create_or_shift_region('ship_3', x + 210, y + 390, 230, 47)
        self._create_or_shift_region('ship_4', x + 210, y + 471, 230, 47)
        self._create_or_shift_region('ship_5', x + 210, y + 552, 230, 47)
        self._create_or_shift_region('ship_6', x + 210, y + 633, 230, 47)
        self._create_or_shift_region('1_slot_unload_equipment', x + 478, y + 294, 4, 4)
        self._create_or_shift_region('2_slot_unload_equipment', x + 478, y + 344, 4, 4)
        self._create_or_shift_region('3_slot_unload_equipment', x + 478, y + 394, 4, 4)
        self._create_or_shift_region('4_slot_unload_equipment', x + 478, y + 444, 4, 4)
        self._create_or_shift_region('5_slot_unload_equipment', x + 478, y + 494, 4, 4)
        self._create_or_shift_region('reinforce_slot_unload_equipment', x + 1162, y + 481, 4, 4)

        self._create_or_shift_region('1_slot_equipment', x + 530, y + 260, 270, 20)
        self._create_or_shift_region('2_slot_equipment', x + 530, y + 307, 270, 20)
        self._create_or_shift_region('3_slot_equipment', x + 530, y + 354, 270, 20)
        self._create_or_shift_region('4_slot_equipment', x + 530, y + 401, 270, 20)
        self._create_or_shift_region('5_slot_equipment', x + 530, y + 448, 270, 20)
        self._create_or_shift_region('reinforce_slot_equipment', x + 1117, y + 471, 20, 20)

        self._create_or_shift_region('equipment_sort_all', x + 783, y + 646, 50, 12)

    def _create_or_shift_region(self, key, x, y, w, h):
        """Helper method for generating or shifting an existing Region's x
        and y position.

        Args:
            key (str): region key.
            x (int): x position of upper-left corner of Region.
            y (int): y position of upper-left corner of Region.
            w (int): width of Region.
            h (int): height of Region.
        """
        if key not in self.r or not isinstance(self.r[key], Region):
            self.r[key] = Region(x, y, w, h)
        else:
            self.r[key].shift_region(x, y)

    def _create_asset_path(self, asset):
        """Helper method for generating the proper OS-safe path to an asset.

        Args:
            asset (str): kcauto-internal asset-style path. This should be in
                the format of '[folder1]|[folder2]|[imagename]'. 'folder1' is
                expected to be within the assets folder of kcauto.

        Returns:
            str: OS-safe path to an asset.
        """
        asset_split = asset.split('|')
        return os.path.join(self.ASSETS_FOLDER, *asset_split)

    def _get_region(self, region):
        """Helper method that returns a Region based on the region passed in.
        If a Region or Match object is passed in, it will return that  object
        as-is. If a string is passed in, it will look up that string key from
        the pre-defined region dictionary and return it if there is a match.

        Args:
            region (Region, Match str): Region/Match object or string key of
                pre-defined region.

        Raises:
            TypeError: string region key was not found in pre-defined region
                list.

        Returns:
            Region/ImageMatch: Region or ImageMatch object.
        """
        if type(region) == str:
            return self.r[region]
        elif isinstance(region, ImageMatch):
            return region
        else:
            raise TypeError("Invalid region specified.")

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
        r = self._get_region(region)
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
        r = self._get_region(region)
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
        r = self._get_region(region)
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
        r = self._get_region(region)
        r.SCAN_RATE = 0.5 #slow down SCAN_RATE to 0.5 for lower CPU usage
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
        r = self._get_region(region)
        r.SCAN_RATE = 0.5 #slow down SCAN_RATE to 0.5 for lower CPU usage
        return r.wait_vanish(self._create_asset_path(asset), wait, similiarity)

    def hover(self, region):
        """Helper method that hovers the mouse cursor over the defined region.

        Args:
            region (Region, Match, str): Region/Match object or pre-defined
                region key.
        """
        
        Log.log_debug_1(f"Hovering over region: {region}")
        
        self.sleep()

        r = self._get_region(region)
        if (cfg.config.general.interaction_mode
                is InteractionModeEnum.DIRECT_CONTROL):
            r.hover()
        elif (cfg.config.general.interaction_mode
                is InteractionModeEnum.CHROME_DRIVER):
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

        r = self._get_region(region)
        if (cfg.config.general.interaction_mode
                is InteractionModeEnum.DIRECT_CONTROL):
            
            corners = [
                r.x + pad[0],  
                r.y + pad[1],
                r.x + r.w + pad[2],
                r.y + r.h + pad[3]
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
        elif (cfg.config.general.interaction_mode
                is InteractionModeEnum.CHROME_DRIVER):
            self._chrome_driver_click_method(r, pad)

        self.sleep()

    def click_existing(
            self, region, asset, similarity=DEFAULT, pad=(0, 0, 0, 0),
            cached=False):
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
        r = self._get_region(region)
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
        r = self._get_region(region)
        r.SCAN_RATE = 0.5 #slow down SCAN_RATE to 0.5 for lower CPU usage
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
        
        Log.log_debug_1(f"Dragging from region: {start_region} to region: {end_region} with pad: {pad}")
        
        self.sleep()

        r_a = self._get_region(start_region)
        r_b = self._get_region(end_region)
        if (cfg.config.general.interaction_mode
                is InteractionModeEnum.DIRECT_CONTROL):
            r_a.hover()
            self.sleep()
            r_b.drag(pad=pad)
            
        elif (cfg.config.general.interaction_mode
                is InteractionModeEnum.CHROME_DRIVER):
            self._chrome_driver_drag_method(r_a, pad, r_b, pad)

        self.sleep()


    def _draw_debug_visualization(self, corners, save_as_file):
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
        
        cv2.rectangle(screen, 
                 (int(corners[0] - self.game_x), int(corners[1] - self.game_y)),  # Top-left point 
                 (int(corners[2] - self.game_x), int(corners[3] - self.game_y)),  # Bottom-right point
                 (0, 255, 0), 
                 2)
        
        Kca.screenshot_log.pop(0) 
        Kca.screenshot_log.append(screen)
        
        if save_as_file:
            
            # Save debug image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            #create folder if not exist
            if not os.path.exists("debug"):
                os.makedirs("debug")
                
            cv2.imwrite(f"debug/click_{timestamp}.png", screen)

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
            self.r['shipgirl'].click()
            api.api.update_from_api({KCSAPIEnum.PORT})
            sts.stats.expedition.expeditions_received += 1
            self.wait('lower_right_corner', 'global|next.png', 20)
            while self.exists('lower_right_corner', 'global|next.png'):
                self.sleep()
                self.r['shipgirl'].click()
                self.r['top'].hover()
                received_expeditions = True
                self.sleep()
                
            import quest.quest_core as qst
            qst.quest.is_quest_dom_cache_dirty = True
            
        return received_expeditions

    def while_wrapper(
            self, conditional_func, internal_func=None, timeout=None,
            attempt_limit=None):
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
            raise FindFailed(
                "Conditional failed by exceeding timeout or attempt limit")

        return True

    def readable_list_join(self, raw_list):
        """Helper method for joining a list into a human-readable string,
        adding 'and' between the second to last and last items as needed.

        Args:
            raw_list (list): list to join

        Returns:
            str: joined string
        """
        display_text = ', '.join([str(i) for i in raw_list])
        display_text = ' and'.join(display_text.rsplit(',', 1))
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

    def _chrome_driver_click_method(self, r, pad):
        """Click method used in Chrome Driver interaction mode.

        Args:
            r (Region, Match): Region/Match region to click
            pad (tuple): padding parameter used to modify click coordinate
        """

        offset_x = randint(pad[0], r.w + pad[2])
        offset_y = randint(pad[1], r.h + pad[3])
        x = r.x - self.css_x
        y = r.y - self.css_y
 
        # Draw debug visualization
            
        corners = [
            r.x + pad[0],  # Top-left corner
            r.y + pad[1],
            r.x + r.w + pad[2],
            r.y + r.h + pad[3]
        ]
            
        self._draw_debug_visualization(corners, arg.args.parsed_args.debug_output)

        #self.visual_hook.Input.synthesizeTapGesture(x= x + offset_x , y=y + offset_y)
        self.visual_hook.Input.dispatchMouseEvent(type = "mouseMoved", x= x + offset_x , y=y + offset_y)
        self.sleep()
        self.visual_hook.Input.dispatchMouseEvent(type = "mousePressed", x= x + offset_x , y=y + offset_y, clickCount = 1, button = "left")
        self.sleep(0.1, 0.2)
        self.visual_hook.Input.dispatchMouseEvent(type = "mouseReleased", x= x + offset_x , y=y + offset_y, clickCount = 1, button = "left")
        self.sleep()

    def _chrome_driver_drag_method(self, r_a, pad_a, r_b, pad_b):
        """Click method used in Chrome Driver interaction mode.

        Args:
            r (Region, Match): Region/Match region to click
            pad (tuple): padding parameter used to modify click coordinate
        """

        offset_x = randint(-pad_a[3], r_a.w + pad_a[1])
        offset_y = randint(-pad_a[0], r_a.h + pad_a[2])
        x = r_a.x - self.css_x
        y = r_a.y - self.css_y

        self.visual_hook.Input.dispatchMouseEvent(type = "mouseMoved", x= x + offset_x , y=y + offset_y)
        self.sleep()
        self.visual_hook.Input.dispatchMouseEvent(type = "mousePressed", x= x + offset_x , y=y + offset_y, clickCount = 1, button = "left")
        self.sleep()
        
        offset_x = randint(-pad_b[3], r_b.w + pad_b[1])
        offset_y = randint(-pad_b[0], r_b.h + pad_b[2])
        x = r_b.x - self.css_x
        y = r_b.y - self.css_y
        
        self.visual_hook.Input.dispatchMouseEvent(type = "mouseMoved", x= x + offset_x , y=y + offset_y)
        self.sleep()
        self.visual_hook.Input.dispatchMouseEvent(type = "mouseReleased", x= x + offset_x , y=y + offset_y, clickCount = 1, button = "left")
        self.sleep()


    def _chrome_driver_hover_method(self, r):
        """hover method used in Chrome Driver interaction mode.

        Args:
            r (Region, Match): Region/Match region to hover 
        """

        offset_x = randint(0, r.w)
        offset_y = randint(0, r.h)
        x = r.x - self.css_x
        y = r.y - self.css_y

        self.visual_hook.Input.dispatchMouseEvent(type = "mouseMoved", x= x + offset_x , y=y + offset_y)

    def cdt_init(self, host="localhost", target = "visual"):
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
            self.api_hook = PyChromeDevTools.ChromeInterface(
                host=host, port=port)
        elif target == "visual":
            self.visual_hook = PyChromeDevTools.ChromeInterface(
                host=host, port=port)
        elif target == "kc3":
            self.kc3_hook = PyChromeDevTools.ChromeInterface(
                host=host, port=port)
        else:
            raise ValueError(
                "Hook target must be either api, visual or kc3.")

        return


    async def get_html(self, url):
        
        port = cfg.config.general.chrome_dev_port
        # Connect to the Chrome browser
        browser = await connect(browserURL='http://localhost:'+str(port))

        # Create a new background tab
        page = await browser.newPage()

        # Navigate the background tab to a desired URL
        await page.goto(url)

        # Retrieve the HTML content
        self.html = await page.content()
        #Log.log_debug(f"kca.html: {self.html}")

        # Close the background tab
        await page.close()

        # Close the connection to the browser
        await browser.disconnect()


    def reload_kc3_strategy_page(self, subpage = ""):
        """method to open/refresh the kc3 strategy page in chrome

        Args:
            subpage (string): The name of sub page to open. (ex. flowchart)
        """
        try:
            asyncio.get_event_loop().run_until_complete(self.get_html(f"chrome-extension://{self.kc3_id}/pages/strategy/strategy.html{subpage}"))
            #Wait for quest panel finish closing
            self.find_kancolle()
        except Exception as e:
            Log.log_warn(f"KC3 strategy page unavailable: {e}")
            self.html = None

        return
    
    def get_quest_dom(self):
        """ method to get the raw quest info form KC3.

        Return:
            raw html text of KC3 quest page
        """
        
        import quest.quest_core as qst
        if qst.quest.is_quest_dom_cache_dirty == False:
            return qst.quest._quest_dom_cache
        
        self.reload_kc3_strategy_page(subpage = "#flowchart")

        if self.html is None:
            Log.log_warn("KC3 unavailable; quest DOM cache not updated, falling back to config defaults.")
            return None

        dom = PyQuery(self.html, parser='html')

        qst.quest._quest_dom_cache = dom("ul#questBox_rootFlow.questTree")
        #Log.log_debug(f"kac.quest_tree_dom:{quest_tree_dom}")
        qst.quest.is_quest_dom_cache_dirty = False
        
        return qst.quest._quest_dom_cache
        
    def get_quest_count(self, target_quest: Quest) -> dict[MapEnum, int] | None:
        """ method to get the remaining action needed for the specified quest.
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
            Log.log_warn(f"KC3 unavailable; cannot get quest count for {target_quest_name}, using config defaults.")
            return None
        
        i = 0
        while True:

            quest_name = quest_tree_dom("div.questInfo").eq(i)(".questIcon").text()
            #Log.log_debug(f"quest_name:{quest_name}")
            
            if quest_name == target_quest_name:
                
                action_raw = quest_tree_dom("div.questInfo").eq(i)(".questCount").attr('title')
                Log.log_debug_1(f"action_raw:{action_raw}")
                if action_raw == None:
                    return None
                action_raw_line = action_raw.split('\n')
                action = {}

                if quest_name == "Bw1":
                    action_raw_line[3] = action_raw_line[3].replace(' ', '/')
                    s_count =           int(action_raw_line[3].split("/")[1]) - int(action_raw_line[3].split("/")[0])
                    action_raw_line[2] = action_raw_line[2].replace(' ', '/')
                    boss_win_count =    int(action_raw_line[2].split("/")[1]) - int(action_raw_line[2].split("/")[0])
                    action_raw_line[1] = action_raw_line[1].replace(' ', '/')
                    boss_count =        int(action_raw_line[1].split("/")[1]) - int(action_raw_line[1].split("/")[0])
                    action_raw_line[0] = action_raw_line[0].replace(' ', '/')
                    sortie_count =      int(action_raw_line[0].split("/")[1]) - int(action_raw_line[0].split("/")[0])

                    if s_count > 0:
                        action[MapEnum.W1_1] = s_count
                    elif boss_win_count > 0:
                        action[MapEnum.W1_5] = boss_win_count 
                    elif boss_count > 0:
                        action[MapEnum.W1_5] = boss_count 
                    elif sortie_count > 0:
                        action[MapEnum.W1_1] = sortie_count

                elif quest_name == "Bq8":
                    action_raw_line[0] = action_raw_line[0].replace(' ', '/')
                    s_1_5_count =        int(action_raw_line[0].split("/")[1]) - int(action_raw_line[0].split("/")[0])
                    action_raw_line[1] = action_raw_line[1].replace(' ', '/')
                    s_7_1_count =        int(action_raw_line[1].split("/")[1]) - int(action_raw_line[1].split("/")[0])
                    action_raw_line[2] = action_raw_line[2].replace(' ', '/')
                    s_7_2_G_count =      int(action_raw_line[2].split("/")[1]) - int(action_raw_line[2].split("/")[0])
                    action_raw_line[3] = action_raw_line[3].replace(' ', '/')
                    s_7_2_M_count =      int(action_raw_line[3].split("/")[1]) - int(action_raw_line[3].split("/")[0])

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
                        line = line.replace(' ', '/')
                        count = int(line.split("/")[1]) - int(line.split("/")[0])
                        import expedition.expedition_core as exp
                        map = exp.expedition.get_exp_enum_from_name(line.split("/")[-1])
                        if count > 0:
                            action[map] = count
                else:

                    for line in action_raw_line:
                        line = line.replace(' ', '/')
                        count = int(line.split("/")[1]) - int(line.split("/")[0])
                        line = line.replace(']', '[')
                        map = line.split("[")[1][1:]
                        if count > 0:
                            
                            if MapEnum("B-"+map).without_quest_enum == MapEnum.W1_6_N:
                                #patch to turn B1-6-N from quest to B1-6
                                action[MapEnum.W1_6] = count
                            else:
                                action[MapEnum("B-"+map).without_quest_enum] = count
                            
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

kca = Kca()
