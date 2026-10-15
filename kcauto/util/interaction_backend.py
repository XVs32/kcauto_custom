"""Single entry point for every input/capture operation in kcauto.

Callers (Kca, Region/Match from pyvisauto, coordinate_system) always talk to
InteractionBackend. The backend validates arguments, picks the click point and
fires callbacks - all in GAME coordinates - and then hands the work to exactly
one InteractionDriver chosen by the configured interaction mode.

Coordinate rule: everything above the driver layer is game space ((0, 0) is the
top-left of the game frame), except regions flagged ``screen_space`` (full
monitor searches), which are desktop pixels. Each driver converts those to what
its transport needs:

    DirectControlDriver  game -> desktop pixels (mss / pyautogui)
    ChromeCdpDriver      game -> browser viewport (CDP); capture uses desktop
    PoiDriver            game as-is (POI frame is the game)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from random import randint

from kca_enums.interaction_modes import InteractionModeEnum
from kca_enums.scroll_directions import ScrollDirectionEnum
from util.pyvisauto import ImageMatch


class InteractionDriver(ABC):
    """One concrete way of seeing and touching the game.

    All point arguments are game coordinates (or desktop coordinates when
    ``region.screen_space`` is True). Converting them is the driver's job.
    """

    name = "interaction"

    def __init__(self, owner):
        self.owner = owner

    # -- lifecycle ---------------------------------------------------------
    @abstractmethod
    def connect(self):
        """Establish hooks/connections and prepare Region defaults."""

    def health_check(self) -> bool:
        """Return False when the connection is stale and needs connect()."""
        return True

    def close(self):
        pass

    # -- locating the game -------------------------------------------------
    @abstractmethod
    def full_region(self):
        """Region that find_kancolle searches for the UI reference point."""

    @abstractmethod
    def resolve_game_origin(self, ref_match) -> tuple[int, int]:
        """Game origin in this driver's 'game_x/game_y' terms."""

    def on_game_located(self):
        """Called after coor.game_x/game_y are up to date."""

    # -- io ----------------------------------------------------------------
    @abstractmethod
    def capture(self, region):
        """Return a PIL image of region."""

    @abstractmethod
    def hover(self, region, x, y): ...

    @abstractmethod
    def click(self, region, x, y, pad): ...

    @abstractmethod
    def scroll(self, region, x, y, pad, direction, amount): ...

    @abstractmethod
    def drag(self, start, start_pt, end, end_pt, pad): ...

    # -- shared helpers ----------------------------------------------------
    @staticmethod
    def wheel_delta(direction):
        if direction is ScrollDirectionEnum.UP:
            return -120
        if direction is ScrollDirectionEnum.DOWN:
            return 120
        raise ValueError(f"Unsupported scroll direction: {direction}")

    @staticmethod
    def corners(region, pad):
        return [
            region.x + pad[0],
            region.y + pad[1],
            region.x + region.w + pad[2],
            region.y + region.h + pad[3],
        ]


class InteractionBackend:
    """The only object that exposes capture/hover/click/scroll/drag."""

    def __init__(self, owner):
        self.owner = owner
        self._drivers: dict[InteractionModeEnum, InteractionDriver] = {}
        # (region, x, y) callbacks, e.g. the click tracker.
        self.click_callback = None
        self.hover_callback = None
        # pyvisauto's Region/Match delegate to us, so code that calls
        # region.click() directly goes through the same entry.
        ImageMatch.backend = self

    # -- driver selection --------------------------------------------------
    @property
    def mode(self):
        # Read config at call time so changing the configured mode does not
        # leave a stale backend selected.
        import config.config_core as cfg

        return cfg.config.general.interaction_mode

    @property
    def driver(self) -> InteractionDriver:
        mode = self.mode
        driver = self._drivers.get(mode)
        if driver is None:
            driver = self._create_driver(mode)
            self._drivers[mode] = driver
        return driver

    def _create_driver(self, mode):
        from util import interaction_drivers as drivers

        if mode is InteractionModeEnum.DIRECT_CONTROL:
            return drivers.DirectControlDriver(self.owner)
        if mode is InteractionModeEnum.CHROME_DRIVER:
            return drivers.ChromeCdpDriver(self.owner)
        if mode is InteractionModeEnum.POI:
            return drivers.PoiDriver(self.owner)
        raise ValueError(f"Unsupported interaction mode: {mode}")

    # -- lifecycle ---------------------------------------------------------
    def connect(self):
        return self.driver.connect()

    def health_check(self):
        return self.driver.health_check()

    def close(self):
        for driver in self._drivers.values():
            driver.close()

    # -- locating the game -------------------------------------------------
    def full_region(self):
        return self.driver.full_region()

    def resolve_game_origin(self, ref_match):
        return self.driver.resolve_game_origin(ref_match)

    def on_game_located(self):
        self.driver.on_game_located()

    # -- io entries --------------------------------------------------------
    def capture(self, region):
        return self.driver.capture(region)

    def hover(self, region, x=None, y=None):
        if x is None or y is None:
            x, y = self._pick_point(region)
        self.driver.hover(region, x, y)
        if self.hover_callback:
            self.hover_callback(region, x, y)

    def click(self, region, pad=(0, 0, 0, 0)):
        x, y = self._pick_point(region, pad)
        self.driver.click(region, x, y, pad)
        if self.click_callback:
            self.click_callback(region, x, y)

    def scroll(self, region, pad=(0, 0, 0, 0), direction=None, amount=1):
        if amount < 1:
            raise ValueError(f"Unsupported scroll amount: {amount}")
        if direction not in (ScrollDirectionEnum.UP, ScrollDirectionEnum.DOWN):
            raise ValueError(f"Unsupported scroll direction: {direction}")
        x, y = self._pick_point(region, pad)
        self.driver.scroll(region, x, y, pad, direction, amount)

    def drag(self, start, end, pad=(0, 0, 0, 0)):
        start_pt = self._pick_point(start, pad)
        end_pt = self._pick_point(end, pad)
        self.driver.drag(start, start_pt, end, end_pt, pad)

    @staticmethod
    def _pick_point(region, pad=(0, 0, 0, 0)):
        """Random point inside region, in the region's own coordinate space.

        pad is an (x1, y1, x2, y2) offset applied to the top-left and
        bottom-right corners respectively.
        """
        x = randint(region.x + pad[0], region.x + region.w + pad[2])
        y = randint(region.y + pad[1], region.y + region.h + pad[3])
        return x, y
