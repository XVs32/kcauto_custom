"""Concrete interaction drivers. See interaction_backend for the contract.

Each driver receives game coordinates (or desktop coordinates for regions with
``screen_space`` set) and converts them itself.
"""

from __future__ import annotations

import mss
import pyautogui
import PyChromeDevTools
from PIL import Image

import api.api_listener as api_listener
import args.args_core as arg
import config.config_core as cfg
import util.coordinate_system as coordinate_system
from constants import API_URL, GAME_H, GAME_W, POI_URL_POSTFIX
from kca_enums.actions import ActionEnum
from util import poi_plugins
from util.interaction_backend import InteractionDriver
from util.logger import Log
from util.poi_client import PoiClient, PoiClientError
from util.pyvisauto import Region

# disable pyautogui failsafe when mouse moves to corner of screen
pyautogui.FAILSAFE = False


def _screen_space(region):
    return getattr(region, "screen_space", False)


def _debug_output():
    return arg.args.parsed_args is not None and arg.args.parsed_args.debug_output


# ---------------------------------------------------------------------------
# Shared base for the two desktop-capture modes (direct control, chrome driver)
# ---------------------------------------------------------------------------
class ChromeHookDriver(InteractionDriver):
    """CDP hooks for API/visual events plus desktop (mss) capture.

    Direct control and Chrome driver both need the CDP hooks (API listener,
    crash detection, browser offset); they only differ in how input is sent.
    """

    name = "Chrome"
    api_hook = None
    poi_hook = None

    # -- lifecycle ---------------------------------------------------------
    def connect(self):
        """Hook into the Kancolle and POI tabs of Chrome through CDP.

        Raises:
            Exception: could not find Kancolle tabs in Chrome.
        """
        Region.default_bounds = None
        Log.log_msg("Hooking into Chrome.")
        self._cdt_init("api")
        self._cdt_init("poi")
        api_listener.api_listener.set_port(cfg.config.general.poi_api_port)
        api_listener.api_listener.start()

        api_tab = api_tab_id = poi_tab = poi_tab_id = None
        for n, tab in enumerate(self.api_hook.tabs):
            if API_URL in tab["url"]:
                api_tab = n
                api_tab_id = tab["id"]
            if tab["url"].endswith(POI_URL_POSTFIX):
                poi_tab = n
                poi_tab_id = tab["id"]

        self.poi_hook.connect_targetID(poi_tab_id)
        Log.log_debug_1(f"Connected to poi tab ({poi_tab}:{poi_tab_id})")

        if api_tab_id is None:
            Log.log_error(
                "No Kantai Collection tab found in Chrome. Shutting down kcauto."
            )
            raise Exception("No running Kantai Collection tab found in Chrome.")

        self.api_hook.connect_targetID(api_tab_id)
        self.api_hook.Page.enable()
        self.api_hook.Network.enable()
        Log.log_debug_1(f"Connected to API tab ({api_tab}:{api_tab_id})")
        Log.log_success("Connected to Chrome")

        coordinate_system.coor.find_game_window_offset()

    def _cdt_init(self, target, host="localhost"):
        port = cfg.config.general.chrome_dev_port
        hook = PyChromeDevTools.ChromeInterface(host=host, port=port)
        if target == "api":
            self.api_hook = hook
            coordinate_system.coor.api_hook = hook
        elif target == "poi":
            self.poi_hook = hook
        else:
            raise ValueError("Hook target must be either api or poi.")

    def health_check(self):
        from util.exceptions import ChromeCrashException

        if self.api_hook is None:
            return False
        for event in self.api_hook.pop_messages():
            method = event.get("method")
            if method in ("Inspector.detached", "Page.frameDetached"):
                return False
            if method == "Inspector.targetCrashed":
                Log.log_warn("Chrome crash detected.")
                raise ChromeCrashException
        return True

    # -- locating the game -------------------------------------------------
    def full_region(self):
        return Region()  # default_bounds is None -> whole monitor, screen space

    def resolve_game_origin(self, ref_match):
        # ref_match comes from a screen-space search, so it is desktop pixels.
        offset = coordinate_system.coor.KC_REF_OFFSET
        return ref_match.x + offset[0], ref_match.y + offset[1]

    def on_game_located(self):
        coordinate_system.coor.find_game_window_offset()

    # -- capture: game -> desktop -----------------------------------------
    def _to_screen(self, region, x, y):
        if _screen_space(region):
            return int(x), int(y)
        coor = coordinate_system.coor
        sx, sy = coor.convert_point(x, y, coor.GAME_TO_WHOLE)
        return int(sx), int(sy)

    def capture(self, region):
        left, top = self._to_screen(region, region.x, region.y)
        with mss.mss() as sct:
            # MSS uses {'top': y, 'left': x, 'width': w, 'height': h}
            shot = sct.grab(
                {
                    "top": top,
                    "left": left,
                    "width": int(region.w),
                    "height": int(region.h),
                }
            )
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def _overlay(self, region, pad, **kwargs):
        self.owner._draw_debug_visualization(
            self.corners(region, pad), _debug_output(), **kwargs
        )


# ---------------------------------------------------------------------------
# Direct control: real mouse through pyautogui
# ---------------------------------------------------------------------------
class DirectControlDriver(ChromeHookDriver):
    name = "Direct control"

    def hover(self, region, x, y):
        sx, sy = self._to_screen(region, x, y)
        pyautogui.moveTo(sx, sy, region.MOUSE_MOVE_SPEED)

    def click(self, region, x, y, pad):
        if _debug_output():
            # Visit the four corners before drawing, as the old pyvisauto
            # debug path did.
            x1, y1, x2, y2 = self.corners(region, pad)
            for cx, cy in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
                self.hover(region, cx, cy)
                self.owner.sleep(0.1)
        self._overlay(region, pad)

        self.hover(region, x, y)
        pyautogui.click()

    def scroll(self, region, x, y, pad, direction, amount):
        self.hover(region, x, y)
        # pyautogui: positive = up, negative = down
        pyautogui.scroll(amount if self.wheel_delta(direction) < 0 else -amount)

    def drag(self, start, start_pt, end, end_pt, pad):
        self.hover(start, *start_pt)
        self.owner.sleep()
        pyautogui.mouseDown()
        self.owner.sleep()
        self.hover(end, *end_pt)
        self.owner.sleep()
        pyautogui.mouseUp()


# ---------------------------------------------------------------------------
# Chrome driver: synthetic mouse events through CDP
# ---------------------------------------------------------------------------
class ChromeCdpDriver(ChromeHookDriver):
    name = "Chrome driver"

    def _to_viewport(self, region, x, y):
        coor = coordinate_system.coor
        mode = (
            coor.WHOLE_TO_VIEWPORT if _screen_space(region) else coor.GAME_TO_VIEWPORT
        )
        return coor.convert_point(x, y, mode)

    def _mouse(self, type_, region, x, y, **kwargs):
        vx, vy = self._to_viewport(region, x, y)
        self.api_hook.Input.dispatchMouseEvent(type=type_, x=vx, y=vy, **kwargs)

    def hover(self, region, x, y):
        self._mouse("mouseMoved", region, x, y)

    def click(self, region, x, y, pad):
        self._overlay(region, pad)
        self._mouse("mouseMoved", region, x, y)
        self.owner.sleep()
        self._mouse("mousePressed", region, x, y, clickCount=1, button="left")
        self.owner.sleep(0.1, 0.2)
        self._mouse("mouseReleased", region, x, y, clickCount=1, button="left")
        self.owner.sleep()

    def scroll(self, region, x, y, pad, direction, amount):
        self._overlay(region, pad, border_color=(0, 0, 255), action=ActionEnum.SCROLL)
        delta_y = self.wheel_delta(direction)
        self._mouse("mouseMoved", region, x, y)
        self.owner.sleep()
        for _ in range(amount):
            self._mouse("mouseWheel", region, x, y, deltaX=0, deltaY=delta_y)
            self.owner.sleep()

    def drag(self, start, start_pt, end, end_pt, pad):
        self._mouse("mouseMoved", start, *start_pt)
        self.owner.sleep()
        self._mouse("mousePressed", start, *start_pt, clickCount=1, button="left")
        self.owner.sleep()
        self._mouse("mouseMoved", end, *end_pt)
        self.owner.sleep()
        self._mouse("mouseReleased", end, *end_pt, clickCount=1, button="left")
        self.owner.sleep()


# ---------------------------------------------------------------------------
# POI: loopback interaction service; its frame already is the game
# ---------------------------------------------------------------------------
class PoiDriver(InteractionDriver):
    name = "POI"
    poi_client = None

    # -- lifecycle ---------------------------------------------------------
    def connect(self):
        Log.log_msg("Connecting to the POI interaction service.")
        if not poi_plugins.check_and_prompt():
            raise Exception(
                "Required POI plugins are missing. See the install "
                "instructions above, then restart POI."
            )
        api_listener.api_listener.set_port(cfg.config.general.poi_api_port)
        api_listener.api_listener.start()

        if self.poi_client is not None:
            self.poi_client.close()
        self.poi_client = PoiClient(port=cfg.config.general.poi_control_port)
        self.poi_client.connect()

        # POI coordinates are game coordinates: every offset is zero.
        coor = coordinate_system.coor
        coor.api_hook = None
        coor.viewport_x = coor.viewport_y = 0
        coor.game_x = coor.game_y = 0
        coor._update_regions()

        Region.default_bounds = (0, 0, GAME_W, GAME_H)
        Log.log_success("Connected to POI")
        return True

    def health_check(self):
        try:
            return self.poi_client is not None and self.poi_client.health_check()
        except (OSError, PoiClientError):
            return False

    def close(self):
        if self.poi_client is not None:
            self.poi_client.close()
            self.poi_client = None

    # -- locating the game -------------------------------------------------
    def full_region(self):
        return Region()  # default_bounds -> the whole game frame

    def resolve_game_origin(self, ref_match):
        # The POI frame is already the game, so its origin stays (0, 0). The
        # reference point only selects which UI skin is on screen.
        return 0, 0

    def on_game_located(self):
        coordinate_system.coor.viewport_x = 0
        coordinate_system.coor.viewport_y = 0

    # -- io: coordinates are used as-is -----------------------------------
    @staticmethod
    def _require_game_space(region):
        if _screen_space(region):
            raise ValueError("POI has no desktop; screen-space regions are unsupported")

    def _client(self):
        if self.poi_client is None:
            raise PoiClientError("POI interaction service is not connected")
        return self.poi_client

    def capture(self, region):
        self._require_game_space(region)
        image = self._client().capture()
        if image.size != (GAME_W, GAME_H):
            image = image.resize((GAME_W, GAME_H), Image.Resampling.LANCZOS)
        left, top = int(region.x), int(region.y)
        return image.crop((left, top, left + int(region.w), top + int(region.h)))

    def hover(self, region, x, y):
        self._require_game_space(region)
        self._client().hover(x, y)
        self.owner.sleep()

    def click(self, region, x, y, pad):
        self._require_game_space(region)
        client = self._client()
        client.hover(x, y)
        self.owner.sleep()
        client.click(x, y)
        self.owner.sleep()
        region._captured = None

    def scroll(self, region, x, y, pad, direction, amount):
        self._require_game_space(region)
        client = self._client()
        delta_y = self.wheel_delta(direction)
        client.hover(x, y)
        self.owner.sleep()
        for _ in range(amount):
            client.scroll(x, y, delta_y)
            self.owner.sleep()
        region._captured = None

    def drag(self, start, start_pt, end, end_pt, pad):
        self._require_game_space(start)
        self._require_game_space(end)
        client = self._client()
        client.hover(*start_pt)
        self.owner.sleep()
        client.drag(*start_pt, *end_pt)
        self.owner.sleep()
        start._captured = None
        end._captured = None
