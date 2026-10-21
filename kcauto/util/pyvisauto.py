import mss
import cv2
import numpy as np
from abc import ABC
from datetime import datetime
from random import randint
from time import sleep


class ImageMatch(ABC):
    """Abstract base class for both Region and Match classes. Ensures that
    convenience variables and methods are shared between the two classes.
    """

    # path to tesseract if it does not exist in the path
    TESSERACT_PATH = ""
    # mouse movement speed
    MOUSE_MOVE_SPEED = 0.2
    # time in seconds to wait between searching for an asset in the wait() and
    # wait_vanish methods().
    SCAN_RATE = 0.05
    # Single input/capture entry point. util.interaction_backend.InteractionBackend
    # registers itself here; every capture/hover/click/scroll below delegates to
    # it, and the backend dispatches per interaction mode and converts
    # coordinates inside each driver.
    backend = None

    _captured = None

    x = 0
    y = 0
    w = 0
    h = 0
    # False: x/y are game coordinates. True: x/y are desktop coordinates,
    # used by a full-monitor region and matches found inside one.
    screen_space = False

    def _tag_match(self, match):
        match.screen_space = getattr(self, "screen_space", False)
        return match

    def capture(self):
        """Capture this region through the interaction backend.

        x/y/w/h are game coordinates (or desktop coordinates when
        screen_space is True); the backend driver converts as needed.
        """
        return self._require_backend().capture(self)

    @classmethod
    def _require_backend(cls):
        if cls.backend is None:
            raise RuntimeError("No interaction backend registered with pyvisauto.")
        return cls.backend

    def _match_template(self, target, template=None, cached=False):
        """Private method for finding matches from either the target asset
        image file or a previously loaded numpy array representation of the
        target asset.

        Args:
            target (str): path to target asset image file.
            template (numpy.ndarray, optional): matrix representation of image
                asset to search for. Used when 'target' was loaded previously.
                Defaults to None.
            cached (bool, optional): Whether or not to search against a cached
                version of the search region. This assumes that the search
                region was captured previously and the content has not changed
                since then.Defaults to False.

        Returns:
            numpy.ndarray: cv2.matchTemplate result of match attempt.
        """
        if template is None:
            template = cv2.imread(target, cv2.IMREAD_GRAYSCALE)
        template.shape[::-1]

        if not cached or self._captured is None:
            capture = self.capture()
            capture_rgb = np.array(capture)
            self._captured = cv2.cvtColor(capture_rgb, cv2.COLOR_BGR2GRAY)

        return cv2.matchTemplate(self._captured, template, cv2.TM_CCOEFF_NORMED)

    def shift_region(self, new_x, new_y):
        """Method for shifting the x and y coordinates of an existing region.
        Useful when the target window moves but you do not necessarily want to
        re-create all regions.

        Args:
            new_x (int): new x coordinate.
            new_y (int): new y coordinate.
        """
        self.x = new_x
        self.y = new_y

    def find(self, target, similarity, cached=False):
        """Match that returns a Match instance for the highest scoring
        match of the target asset within the region.

        Args:
            target (str): path to target asset image file.
            similarity (float): min similarity score of target asset in region.
            cached (bool, optional): whether or not to search against the
                cached copy of the region. Assumes that this region was
                captured previously and has not changed since then. Defaults to
                False.

        Raises:
            FindFailed: raised if the target asset does not exist in the
                region.

        Returns:
            Match: Match instance representation of the match
        """
        template = cv2.imread(target, cv2.IMREAD_GRAYSCALE)
        match = self._match_template(target, template, cached=cached)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
        if max_val < similarity:
            raise FindFailed(f"{target} not found in {self}!")
        return self._tag_match(
            Match(
                target,
                self.x + max_loc[0],
                self.y + max_loc[1],
                len(template[0]),
                len(template),
                max_val,
            )
        )

    def find_all(self, target, similarity, cached=False):
        """Method that finds all matches of the target asset within the region.

        Args:
            target (str): path to target asset image file.
            similarity (float): min similarity score of target asset in region.
            cached (bool, optional): whether or not to search against the
                cached copy of the region. Assumes that this region was
                captured previously and has not changed since then. Defaults to
                False.

        Returns:
            [Match]: list of Match instances, each representing a match in
                the region.
        """
        template = cv2.imread(target, cv2.IMREAD_GRAYSCALE)
        matches = self._match_template(target, template, cached=cached)
        matches_filtered = np.where(matches >= similarity)
        match_list = []
        for match in zip(*matches_filtered[::-1]):
            match_list.append(
                self._tag_match(
                    Match(
                        target,
                        self.x + match[0],
                        self.y + match[1],
                        len(template[0]),
                        len(template),
                        matches[match[1]][match[0]],
                    )
                )
            )
        return match_list

    def exists(self, target, similarity, cached=False):
        """Method that checks whether or not the target asset exists within the
        region.

        Args:
            target (str): path to target asset image file.
            similarity (float): min similarity score of target asset in region.
            cached (bool, optional): whether or not to search against the
                cached copy of the region. Assumes that this region was
                captured previously and has not changed since then. Defaults to
                False.

        Returns:
            bool: True if the target asset was found. False otherwise.
        """
        match = self._match_template(target, cached=cached)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
        if max_val < similarity:
            return False
        return True

    def wait(self, target, wait, similarity):
        """Method that waits for the target asset to appear within the region.

        Args:
            target (str): path to target asset image file.
            wait (int): max time in seconds to wait for the asset to appear.
            similarity (float): min similarity score of target asset in region.

        Raises:
            FindFailed: raised if target asset does not exist in region after
                the max wait time.

        Returns:
            Match: Match instance.
        """
        start = datetime.now()
        now = datetime.now()
        while (now - start).total_seconds() < wait:
            try:
                match = self.find(target, similarity)
                return match
            except FindFailed:
                sleep(self.SCAN_RATE)
                now = datetime.now()
        raise FindFailed(
            f"{target} not found in {self} after waiting for {wait} seconds."
        )

    def wait_vanish(self, target, wait, similarity):
        """Method that returns once the target asset no longer exists in the
        region.

        Args:
            target (str): path to target asset image file.
            wait (int): max time in seconds to wait for the asset to disappear.
            similarity (float): min similarity score of target asset in region.

        Raises:
            VanishFailed: raised if target asset exists in region after the max
                wait time.

        Returns:
            True: asset no longer exists in region.
        """
        start = datetime.now()
        now = datetime.now()
        while (now - start).total_seconds() < wait:
            if not self.exists(target, similarity):
                return True
            sleep(self.SCAN_RATE)
            now = datetime.now()
        raise VanishFailed(
            f"{target} still in {self} after waiting for {wait} seconds."
        )

    def hover(self, x=None, y=None):
        """Hover over (x, y), or a random point within the region."""
        self._require_backend().hover(self, x, y)

    def click(self, pad=(0, 0, 0, 0)):
        """Click a random point within the region.

        Args:
            pad (tuple, optional): offset of click area, (x1, y1, x2, y2).
                Defaults to (0, 0, 0, 0).
        """
        self._require_backend().click(self, pad)

    def scroll(self, pad=(0, 0, 0, 0), *, direction, amount=1):
        """Scroll at a random point within the region.

        Args:
            pad (tuple, optional): offset of scroll area, (x1, y1, x2, y2).
            direction (ScrollDirectionEnum): Scroll direction.
            amount (int, optional): Number of scroll steps to perform.
        """
        self._require_backend().scroll(self, pad, direction, amount)

    def drag(self, end, pad=(0, 0, 0, 0)):
        """Press at a random point here, release at a random point in end."""
        self._require_backend().drag(self, end, pad)

    def save_screenshot(self, filename):
        """Method for saving a screenshot of the region to a file.

        Args:
            filename (str): path to save screenshot to.
        """
        capture = self.capture()
        capture.save(filename)


class Region(ImageMatch):
    """Class used to define a (search) region. Create a Region to visually
    search within it or to use other ImageMatch public methods.
    """

    default_bounds = None

    def __init__(self, x=None, y=None, w=None, h=None):
        """Initialize a Region instance. Leave all parameters blank to create
        a region for the entire screen. Fill in all parameters otherwise.

        Args:
            x (int, optional): x-coordinate of upper-left corner of region in
                pixels. Defaults to None.
            y (int, optional): y-coordinate of upper-left corner of region in
                pixels. Defaults to None.
            w (int, optional): width of region in pixels. Defaults to None.
            h (int, optional): height of region in pixels. Defaults to None.

        Raises:
            ValueError: raised when one or more, but not all, parameters are
                specified.
        """
        self.MOUSE_MOVE_SPEED = Region.MOUSE_MOVE_SPEED
        if (
            x is None
            and y is None
            and w is None
            and h is None
            and Region.default_bounds is not None
        ):
            self.x, self.y, self.w, self.h = Region.default_bounds
        elif x is None and y is None and w is None and h is None:
            with mss.mss() as sct:
                screen = sct.monitors[0]
            self.x = screen["left"]
            self.y = screen["top"]
            self.w = screen["width"]
            self.h = screen["height"]
            # Full-monitor coordinates are desktop pixels, not game pixels.
            self.screen_space = True
        else:
            if x is None or y is None or w is None or h is None:
                raise ValueError("Parameters must be all or nothing.")
            self.x = x
            self.y = y
            self.w = w
            self.h = h

    def __repr__(self):
        return f"[ X:{self.x}, Y:{self.y}, W:{self.w}, H:{self.h} ]"


class Match(ImageMatch):
    """Class returned when an image asset search is successful. Not intended
    to be instantiated manually.
    """

    def __init__(self, name, x, y, w, h, similarity):
        self.MOUSE_MOVE_SPEED = Match.MOUSE_MOVE_SPEED
        self.name = name
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.similarity = similarity

    def __repr__(self):
        return (
            f"[ {self.name}: X:{self.x}, Y:{self.y}, W:{self.w}, H:{self.h}, "
            f"{self.similarity:.5f} ]"
        )


class FindFailed(Exception):
    """Raised when an asset could not be found on screen."""

    pass


class VanishFailed(Exception):
    """Raised when an asset expected to disappear does not disappear by the
    timeout time.
    """

    pass
