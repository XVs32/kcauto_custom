"""Unified input/capture backend for kcauto interaction modes.

The backend owns mode-specific dispatch while Kca remains the public API.
Coordinates passed to these methods are the existing whole-screen Region
coordinates used by coordinate_system.coor.
"""
from __future__ import annotations

from random import randint

from kca_enums.interaction_modes import InteractionModeEnum
from kca_enums.scroll_directions import ScrollDirectionEnum
from util.logger import Log
from util.poi_client import PoiClientError


class InteractionBackend:
    """Adapter that routes common interaction operations to one provider."""

    def __init__(self, owner):
        self.owner = owner

    @property
    def mode(self):
        # Read config at call time so changing the configured mode does not
        # leave a stale backend selected.
        import config.config_core as cfg
        return cfg.config.general.interaction_mode

    def capture(self, region):
        if self.mode is InteractionModeEnum.POI:
            return self.owner._poi_capture_method(region)
        # Direct control and CDP continue using pyvisauto's configured capture.
        return None

    def hover(self, region):
        if self.mode is InteractionModeEnum.DIRECT_CONTROL:
            region.hover()
        elif self.mode is InteractionModeEnum.CHROME_DRIVER:
            self.owner._chrome_driver_hover_method(region)
        elif self.mode is InteractionModeEnum.POI:
            self.owner._poi_hover_method(region, region.x + region.w // 2,
                                         region.y + region.h // 2)
        else:
            raise ValueError(f"Unsupported interaction mode: {self.mode}")

    def click(self, region, pad=(0, 0, 0, 0)):
        if self.mode is InteractionModeEnum.DIRECT_CONTROL:
            region.click(pad=pad)
        elif self.mode is InteractionModeEnum.CHROME_DRIVER:
            self.owner._chrome_driver_click_method(region, pad)
        elif self.mode is InteractionModeEnum.POI:
            x = randint(region.x + pad[0], region.x + region.w + pad[2])
            y = randint(region.y + pad[1], region.y + region.h + pad[3])
            self.owner._poi_click_method(region, x, y)
        else:
            raise ValueError(f"Unsupported interaction mode: {self.mode}")

    def scroll(self, region, pad, direction, amount=1):
        if amount < 1:
            raise ValueError(f"Unsupported scroll amount: {amount}")
        if self.mode is InteractionModeEnum.DIRECT_CONTROL:
            region.scroll(pad=pad, direction=direction, amount=amount)
        elif self.mode is InteractionModeEnum.CHROME_DRIVER:
            self.owner._chrome_driver_scroll_method(region, pad, direction, amount)
        elif self.mode is InteractionModeEnum.POI:
            x = randint(region.x + pad[0], region.x + region.w + pad[2])
            y = randint(region.y + pad[1], region.y + region.h + pad[3])
            self.owner._poi_scroll_method(region, x, y, direction, amount)
        else:
            raise ValueError(f"Unsupported interaction mode: {self.mode}")

    def drag(self, start, end, pad=(0, 0, 0, 0)):
        if self.mode is InteractionModeEnum.DIRECT_CONTROL:
            start.hover()
            end.drag(pad=pad)
        elif self.mode is InteractionModeEnum.CHROME_DRIVER:
            self.owner._chrome_driver_drag_method(start, pad, end, pad)
        elif self.mode is InteractionModeEnum.POI:
            self.owner._poi_drag_method(start, pad, end, pad)
        else:
            raise ValueError(f"Unsupported interaction mode: {self.mode}")

    def health_check(self):
        if self.mode is InteractionModeEnum.POI:
            if self.owner.poi_client is None or not self.owner.poi_client.health_check():
                raise PoiClientError("POI health check failed")
            return True
        hook = self.owner.api_hook
        if hook is None:
            return False
        for event in hook.pop_messages():
            method = event.get("method")
            if method in ("Inspector.detached", "Page.frameDetached"):
                return False
            if method == "Inspector.targetCrashed":
                from util.exceptions import ChromeCrashException
                raise ChromeCrashException
        return True

    def close(self):
        if self.owner.poi_client is not None:
            self.owner.poi_client.close()
            self.owner.poi_client = None
