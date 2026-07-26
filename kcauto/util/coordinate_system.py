
import cv2
import numpy as np
import time

from datetime import datetime
import os

import args.args_core as arg
from util.logger import Log
from util.pyvisauto import Region, ImageMatch

from constants import (
    GAME_W,
    GAME_H,
    VISUAL_URL,
    API_URL,
    EXACT,
    DEFAULT,
    SLEEP_MODIFIER,
)

class CoordinateSystem(object):
    """coordinate system class."""
    BROWSER_REF_ENTROPY_THRESHOLD = 0.5
    BROWSER_REF_SIZE = 100
    KC_REF_OFFSET = (-144, 0)

    visual_hook = None
    last_ui = None

    viewport_x = None
    viewport_y = None
    game_x = None
    game_y = None

    r = {}

    WHOLE_TO_VIEWPORT = 0
    VIEWPORT_TO_WHOLE = 1
    WHOLE_TO_GAME = 2
    GAME_TO_WHOLE = 3
    VIEWPORT_TO_GAME = 4
    GAME_TO_VIEWPORT = 5
    

    def __init__(self):
        pass

    def find_game_window_offset(self):
        """Method that finds the game window offset for chrome driver"""
        Log.log_msg("Finding browser offset")

        whole_screen_region = Region()
        whole_screen_origin = (whole_screen_region.x, whole_screen_region.y)
        Log.log_debug_1(f"whole_screen_region.x: {whole_screen_region.x}")
        Log.log_debug_1(f"whole_screen_region.y: {whole_screen_region.y}")
        Log.log_debug_1(f"whole_screen_region.w: {whole_screen_region.w}")
        Log.log_debug_1(f"whole_screen_region.h: {whole_screen_region.h}")

        retry = 0
        max_retries = 5
        retry_delay = 1

        while retry < max_retries:
            try:
                whole_screen = whole_screen_region.capture()
                whole_screen_rgb = np.array(whole_screen)
                whole_screen_gray = cv2.cvtColor(whole_screen_rgb, cv2.COLOR_BGR2GRAY)

                viewport_screenshot = self._capture_browser_screenshot_gray()

                if arg.args.parsed_args.debug_output:
                    self._debug_save_all_browser_refs(viewport_screenshot)
                    self._debug_draw_browser_slide_windows(viewport_screenshot)

                Log.log_debug_1(
                    f"chrome driver browser size: {(viewport_screenshot.shape[1], viewport_screenshot.shape[0])}"
                )

                valid_ref_found = False

                for ref_info in self._iter_browser_ref_regions(viewport_screenshot):
                    ref_entropy = ref_info["entropy"]
                    window_x = ref_info["window_x"]
                    window_y = ref_info["window_y"]
                    Log.log_debug_1(
                        f"ref entropy at window ({window_x}, {window_y}): {ref_entropy:.4f}"
                    )

                    if ref_entropy < self.BROWSER_REF_ENTROPY_THRESHOLD:
                        continue

                    valid_ref_found = True
                    if self._try_browser_offset_match(
                        whole_screen_origin,
                        whole_screen_gray,
                        ref_info["ref"],
                        ref_info["ref_x"],
                        ref_info["ref_y"],
                    ):
                        return True

                if not valid_ref_found:
                    Log.log_warn(
                        "No valid reference clip found in sliding windows, falling back to full browser screenshot."
                    )
                    if self._try_browser_offset_match(
                        whole_screen_origin,
                        whole_screen_gray,
                        viewport_screenshot,
                        0,
                        0,
                    ):
                        return True
                    raise ValueError(
                        "No valid sliding window reference found and full browser match failed"
                    )
                else:
                    raise ValueError("No browser offset found from valid references")

            except Exception as e:
                Log.log_error(f"Attempt {retry + 1}/{max_retries} failed: {str(e)}")
                retry += 1
                if retry < max_retries:
                    time.sleep(retry_delay)
                    continue
                else:
                    Log.log_error("Failed to find browser offset after max retries")

                    if self.viewport_x is None or self.viewport_y is None:
                        Log.log_error(
                            "Browser offset not found. Please check your Chrome setup."
                        )
                        exit(1)

                    return False

    def _capture_browser_screenshot_gray(self):
        """Capture the browser screenshot and decode it to grayscale."""

        import base64

        screenshot_raw = self.visual_hook.Page.captureScreenshot()

        if screenshot_raw is None or not screenshot_raw:
            raise ValueError("Failed to capture screenshot from Chrome")

        if len(screenshot_raw) == 0 or "result" not in screenshot_raw[0]:
            raise ValueError("Invalid screenshot data structure")

        result = screenshot_raw[0]["result"]
        if "data" not in result:
            raise ValueError("No image data in screenshot result")

        screenshot_data = base64.b64decode(result["data"])
        screenshot_gray = cv2.imdecode(
            np.frombuffer(screenshot_data, np.uint8), cv2.IMREAD_GRAYSCALE
        )
        if screenshot_gray is None:
            raise ValueError("Failed to decode browser screenshot")
        return screenshot_gray

    def _build_browser_ref_layout(self, screenshot_gray):
        """Build reusable layout values for browser ref scanning."""
        slide_window_width = min(GAME_W // 2, screenshot_gray.shape[1])
        slide_window_height = min(GAME_H // 2, screenshot_gray.shape[0])
        ref_size = min(self.BROWSER_REF_SIZE, slide_window_width, slide_window_height)
        ref_origin_x = (slide_window_width - ref_size) // 2
        ref_origin_y = (slide_window_height - ref_size) // 2

        return {
            "slide_window_width": slide_window_width,
            "slide_window_height": slide_window_height,
            "ref_size": ref_size,
            "ref_origin_x": ref_origin_x,
            "ref_origin_y": ref_origin_y,
            "x_positions": self._build_sliding_positions(
                screenshot_gray.shape[1], slide_window_width, slide_window_width
            ),
            "y_positions": self._build_sliding_positions(
                screenshot_gray.shape[0], slide_window_height, slide_window_height
            ),
        }

    def _iter_browser_ref_regions(self, screenshot_gray):
        """Yield sliding windows and centered refs from the browser screenshot."""
        layout = self._build_browser_ref_layout(screenshot_gray)
        slide_window_width = layout["slide_window_width"]
        slide_window_height = layout["slide_window_height"]
        ref_size = layout["ref_size"]
        ref_origin_x = layout["ref_origin_x"]
        ref_origin_y = layout["ref_origin_y"]

        for window_y in layout["y_positions"]:
            for window_x in layout["x_positions"]:
                slide_window = screenshot_gray[
                    window_y : window_y + slide_window_height,
                    window_x : window_x + slide_window_width,
                ]
                ref = slide_window[
                    ref_origin_y : ref_origin_y + ref_size,
                    ref_origin_x : ref_origin_x + ref_size,
                ]
                yield {
                    "window_x": window_x,
                    "window_y": window_y,
                    "slide_window_width": slide_window_width,
                    "slide_window_height": slide_window_height,
                    "ref_x": window_x + ref_origin_x,
                    "ref_y": window_y + ref_origin_y,
                    "ref_size": ref_size,
                    "ref": ref,
                    "entropy": self._calc_grayscale_entropy(ref),
                }

    def _try_browser_offset_match(
        self, whole_screen_origin, whole_screen_gray, ref, start_x, start_y
    ):
        """Try matching a browser reference image against the full screen."""
        match = cv2.matchTemplate(whole_screen_gray, ref, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
        Log.log_debug_1(f"start_x: {start_x}")
        Log.log_debug_1(f"start_y: {start_y}")
        Log.log_debug_1(f"max_loc: {max_loc}")

        if max_val < 0.9:
            Log.log_error(f"Match value {max_val} is below threshold")
            return False

        self.viewport_x = whole_screen_origin[0] + max_loc[0] - start_x
        self.viewport_y = whole_screen_origin[1] + max_loc[1] - start_y
        Log.log_success(
            f"Browser offset found at X: {self.viewport_x}, Y: {self.viewport_y}"
        )
        return True

    def _build_sliding_positions(self, full_size, window_size, step_size):
        """Build side-by-side sliding window positions using a fixed step."""
        if full_size <= window_size:
            return [0]

        return list(range(0, full_size - window_size + 1, step_size))

    def _debug_save_all_browser_refs(self, screenshot_gray):
        """Save all sliding-window reference images without stopping early."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = os.path.join("debug", f"browser_refs_{timestamp}")
        os.makedirs(debug_dir, exist_ok=True)

        saved_count = 0
        for ref_info in self._iter_browser_ref_regions(screenshot_gray):
            entropy = ref_info["entropy"]
            status = (
                "valid" if entropy >= self.BROWSER_REF_ENTROPY_THRESHOLD else "blank"
            )
            filename = f"ref_x{ref_info['window_x']}_y{ref_info['window_y']}_entropy_{entropy:.4f}_{status}.png"
            cv2.imwrite(os.path.join(debug_dir, filename), ref_info["ref"])
            saved_count += 1

        Log.log_msg(f"Saved {saved_count} browser refs to {debug_dir}")
        return debug_dir


    def _debug_draw_browser_slide_windows(self, screenshot_gray):
        """Draw slide windows and ref regions on the browser screenshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = "debug"
        os.makedirs(debug_dir, exist_ok=True)

        debug_image = cv2.cvtColor(screenshot_gray, cv2.COLOR_GRAY2BGR)
        for ref_info in self._iter_browser_ref_regions(screenshot_gray):
            cv2.rectangle(
                debug_image,
                (ref_info["window_x"], ref_info["window_y"]),
                (
                    ref_info["window_x"] + ref_info["slide_window_width"],
                    ref_info["window_y"] + ref_info["slide_window_height"],
                ),
                (0, 255, 0),
                2,
            )
            cv2.rectangle(
                debug_image,
                (ref_info["ref_x"], ref_info["ref_y"]),
                (
                    ref_info["ref_x"] + ref_info["ref_size"],
                    ref_info["ref_y"] + ref_info["ref_size"],
                ),
                (0, 0, 255),
                2,
            )
            text_x = ref_info["ref_x"] + 4
            text_y = ref_info["ref_y"] + min(ref_info["ref_size"] - 6, 18)
            cv2.putText(
                debug_image,
                f"{ref_info['entropy']:.2f}",
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )

        output_path = os.path.join(debug_dir, f"browser_slide_windows_{timestamp}.png")
        cv2.imwrite(output_path, debug_image)
        Log.log_msg(f"Saved browser slide window debug image to {output_path}")
        return output_path

    def _calc_grayscale_entropy(self, image):
        """Calculate Shannon entropy for a grayscale image."""
        hist = cv2.calcHist([image], [0], None, [256], [0, 256])
        total = float(hist.sum())
        if total == 0:
            return 0.0

        probabilities = hist / total
        probabilities = probabilities[probabilities > 0]
        return float(-np.sum(probabilities * np.log2(probabilities)))



    def convert(self, src, mode):
        dst = Region()
        if mode == self.WHOLE_TO_VIEWPORT:
            dst.x = src.x - self.viewport_x
            dst.y = src.y - self.viewport_y
            return dst
        elif mode == self.VIEWPORT_TO_WHOLE:
            dst.x = src.x + self.viewport_x
            dst.y = src.y + self.viewport_y
            return  dst
        elif mode == self.WHOLE_TO_GAME:
            dst.x = src.x -  self.game_x
            dst.y = src.y - self.game_y
            return dst
        elif mode == self.GAME_TO_WHOLE:
            dst.x = src.x + self.game_x
            dst.y = src.y + self.game_y
            return dst
        elif mode == self.VIEWPORT_TO_GAME:
            dst.x = src.x + self.viewport_x - self.game_x
            dst.y = src.y + self.viewport_y - self.game_y
            return dst
        elif mode == self.GAME_TO_VIEWPORT:
            dst.x = src.x + self.game_x - self.viewport_x
            dst.y = src.y + self.game_y - self.viewport_y
            return dst
        else:
            raise ValueError("Invalid mode")

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
        self._create_or_shift_region("kc", x, y, w, h)
        self._create_or_shift_region("left", x, y, hw, h)
        self._create_or_shift_region("right", x + hw, y, hw, h)
        self._create_or_shift_region("upper", x, y, w, hh)
        self._create_or_shift_region("lower", x, y + hh, w, hh)
        self._create_or_shift_region("upper_left", x, y, hw, hh)
        self._create_or_shift_region("upper_right", x + hw, y, hw, hh)
        self._create_or_shift_region("lower_left", x, y + hh, hw, hh)
        self._create_or_shift_region("lower_right", x + hw, y + hh, hw, hh)
        self._create_or_shift_region("lower_right_corner", x + 1100, y + 620, 100, 100)
        self._create_or_shift_region("center", x + 225, y + 180, 750, 360)
        self._create_or_shift_region("top", x + 400, y + 12, 800, 30)
        self._create_or_shift_region("shipgirl", x + 700, y + 130, 400, 420)
        self._create_or_shift_region("combat_click", x + 700, y + 680, 200, 30)
        # function-specific regions
        self._create_or_shift_region("expedition_flag", x + 750, y + 20, 70, 50)
        self._create_or_shift_region("top_menu", x + 185, y + 50, 800, 50)
        self._create_or_shift_region("top_menu_quest", x + 790, y + 50, 105, 45)
        self._create_or_shift_region("home_menu", x + 45, y + 130, 500, 490)
        self._create_or_shift_region("side_menu", x, y + 190, 145, 400)
        self._create_or_shift_region("top_submenu", x + 145, y + 145, 1055, 70)
        self._create_or_shift_region("quest_status", x + 1065, y + 165, 95, 500)
        self._create_or_shift_region("check_damage_combat", x + 470, y + 215, 50, 475)
        self._create_or_shift_region("lbas", x + 500, y + 5, 200, 45)
        self._create_or_shift_region("lbas_mode_switch", x + 1135, y + 200, 55, 80)
        self._create_or_shift_region("7th_next", x + 386, y + 400, 27, 27)
        # combat-related regions
        self._create_or_shift_region("c_world", x + 180, y + 635, 650, 65)
        self._create_or_shift_region("formation_line_ahead", x + 596, y + 256, 250, 44)
        self._create_or_shift_region("formation_double_line", x + 791, y + 256, 250, 44)
        self._create_or_shift_region("formation_diamond", x + 989, y + 256, 150, 44)
        self._create_or_shift_region("formation_echelon", x + 596, y + 495, 252, 44)
        self._create_or_shift_region(
            "formation_line_abreast", x + 791, y + 495, 253, 44
        )
        self._create_or_shift_region("formation_vanguard", x + 989, y + 495, 150, 44)
        self._create_or_shift_region(
            "formation_combined_fleet_1", x + 640, y + 240, 215, 45
        )
        self._create_or_shift_region(
            "formation_combined_fleet_2", x + 890, y + 240, 215, 45
        )
        self._create_or_shift_region(
            "formation_combined_fleet_3", x + 640, y + 445, 215, 45
        )
        self._create_or_shift_region(
            "formation_combined_fleet_4", x + 890, y + 445, 215, 45
        )
        # factory-related regions
        self._create_or_shift_region(
            "build_slot_1_stat_region", x + 595, y + 180, 150, 60
        )
        self._create_or_shift_region(
            "build_slot_2_stat_region", x + 595, y + 305, 150, 60
        )
        self._create_or_shift_region("build_slot_1_region", x + 900, y + 260, 60, 15)
        self._create_or_shift_region("build_slot_2_region", x + 900, y + 380, 60, 15)
        self._create_or_shift_region("order_confirm_region", x + 975, y + 635, 200, 50)
        self._create_or_shift_region("use_item_region", x + 635, y + 580, 100, 20)
        self._create_or_shift_region("develop_region", x + 215, y + 480, 200, 50)
        self._create_or_shift_region("order_oil_region_1", x + 552, y + 226, 10, 10)
        self._create_or_shift_region("order_oil_region_10", x + 742, y + 194, 10, 10)
        self._create_or_shift_region("order_oil_region_100", x + 742, y + 236, 10, 10)
        self._create_or_shift_region("order_ammo_region_1", x + 552, y + 420, 10, 10)
        self._create_or_shift_region("order_ammo_region_10", x + 742, y + 390, 10, 10)
        self._create_or_shift_region("order_ammo_region_100", x + 742, y + 430, 10, 10)
        self._create_or_shift_region("order_steel_region_1", x + 890, y + 226, 10, 10)
        self._create_or_shift_region("order_steel_region_10", x + 1085, y + 194, 10, 10)
        self._create_or_shift_region(
            "order_steel_region_100", x + 1085, y + 236, 10, 10
        )
        self._create_or_shift_region("order_bauxite_region_1", x + 890, y + 420, 10, 10)
        self._create_or_shift_region(
            "order_bauxite_region_10", x + 1085, y + 390, 10, 10
        )
        self._create_or_shift_region(
            "order_bauxite_region_100", x + 1085, y + 430, 10, 10
        )

        # expedition-related regions
        self._create_or_shift_region(
            "expedition_scoll_down_mark", x + 420, y + 600, 70, 20
        )
        self._create_or_shift_region("expedition_scoll_down", x + 440, y + 610, 20, 20)

        self._create_or_shift_region("expedition_scoll_up", x + 440, y + 200, 20, 20)

        # equipment-related regions
        self._create_or_shift_region("equipment_panel", x + 455, y + 226, 125, 268)
        self._create_or_shift_region("ship_1", x + 210, y + 228, 230, 47)
        self._create_or_shift_region("ship_2", x + 210, y + 309, 230, 47)
        self._create_or_shift_region("ship_3", x + 210, y + 390, 230, 47)
        self._create_or_shift_region("ship_4", x + 210, y + 471, 230, 47)
        self._create_or_shift_region("ship_5", x + 210, y + 552, 230, 47)
        self._create_or_shift_region("ship_6", x + 210, y + 633, 230, 47)
        self._create_or_shift_region("1_slot_unload_equipment", x + 478, y + 294, 4, 4)
        self._create_or_shift_region("2_slot_unload_equipment", x + 478, y + 344, 4, 4)
        self._create_or_shift_region("3_slot_unload_equipment", x + 478, y + 394, 4, 4)
        self._create_or_shift_region("4_slot_unload_equipment", x + 478, y + 444, 4, 4)
        self._create_or_shift_region("5_slot_unload_equipment", x + 478, y + 494, 4, 4)
        self._create_or_shift_region(
            "reinforce_slot_unload_equipment", x + 1162, y + 481, 4, 4
        )

        self._create_or_shift_region("1_slot_equipment", x + 530, y + 260, 270, 20)
        self._create_or_shift_region("2_slot_equipment", x + 530, y + 307, 270, 20)
        self._create_or_shift_region("3_slot_equipment", x + 530, y + 354, 270, 20)
        self._create_or_shift_region("4_slot_equipment", x + 530, y + 401, 270, 20)
        self._create_or_shift_region("5_slot_equipment", x + 530, y + 448, 270, 20)
        self._create_or_shift_region(
            "reinforce_slot_equipment", x + 1117, y + 471, 20, 20
        )

        self._create_or_shift_region("equipment_sort_all", x + 783, y + 646, 50, 12)

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

    def get_region(self, region):
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

coor = CoordinateSystem()
