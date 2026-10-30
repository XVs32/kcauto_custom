import numpy as np
import util.coordinate_system as coordinate_system
from constants import GAME_W, GAME_H


class ClickTracker(object):
    click_matrix = None

    def __init__(self):
        try:
            raw = np.load("click_matrix.npz")
            self.click_matrix = raw["click_matrix"]
        except FileNotFoundError:
            self.click_matrix = np.zeros(shape=(GAME_H, GAME_W))

    def track_click(self, r, x, y):
        # (x, y) is a game coordinate, except for screen-space regions
        # (full-monitor searches such as the splash screen), which carry
        # desktop pixels and need converting.
        if getattr(r, "screen_space", False):
            coor = coordinate_system.coor
            x, y = coor.convert_point(x, y, coor.WHOLE_TO_GAME)

        x, y = int(x), int(y)
        if 0 <= x < GAME_W and 0 <= y < GAME_H:
            self.click_matrix[y][x] += 1

    def export(self):
        np.savez("click_matrix", click_matrix=self.click_matrix)


click_tracker = ClickTracker()
