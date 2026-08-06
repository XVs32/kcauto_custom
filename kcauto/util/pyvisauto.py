import mss
from PIL import Image
import cv2
import numpy as np
import pyautogui
from abc import ABC
from datetime import datetime
from random import randint
from time import sleep
from kca_enums.scroll_directions import ScrollDirectionEnum


# disable pyautogui failsafe when mouse moves to corner of screen
pyautogui.FAILSAFE = False


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
    # assign the method for overriding the hover methods to this class
    # variable. Should accept the parameters (region, x, y)
    override_hover_method = None
    # assign the callback method for hovers to this class variable. Should
    # accept the parameters (region, x, y)
    hover_callback = None
    # assign the method for overriding the click methods to this class
    # variable. Should accept the parameters (region, x, y, pad)
    override_click_method = None
    # assign the method for overriding the scroll methods to this class
    # variable. Should accept the parameters (region, x, y, pad, direction, amount)
    override_scroll_method = None
    # assign the method for overriding screenshot capture to this class
    # variable. Should accept the region and return a PIL.Image.
    override_capture_method = None
    # assign the callback method for click to this class variable. Should
    # accept the parameters (region, x, y)
    click_callback = None

    _captured = None

    x = 0
    y = 0
    w = 0
    h = 0

    def capture(self):
        """Private method for capturing the defined region using MSS.

        Returns:
            PIL.Image: object representing captured region.
        """
        if ImageMatch.override_capture_method:
            return ImageMatch.override_capture_method(self)

        with mss.mss() as sct:
            # Ensure all coordinates are integers and not None
            # MSS uses {'top': y, 'left': x, 'width': w, 'height': h}
            region = {
                "top": int(self.y),
                "left": int(self.x),
                "width": int(self.w),
                "height": int(self.h),
            }

            screenshot = sct.grab(region)

            # Convert MSS screenshot to PIL Image
            return Image.frombytes(
                "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
            )

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
        return Match(
            target,
            self.x + max_loc[0],
            self.y + max_loc[1],
            len(template[0]),
            len(template),
            max_val,
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
                Match(
                    target,
                    self.x + match[0],
                    self.y + match[1],
                    len(template[0]),
                    len(template),
                    matches[match[1]][match[0]],
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
        """Method to hover over a random point within the region. If an
        override_hover_method exists, it will be used instead of the default
        pyautogui moveTo method. If a hover_callback is specified, it will be
        called after the hover action.
        """

        if x is None or y is None:
            x = randint(self.x, self.x + self.w)
            y = randint(self.y, self.y + self.h)

        if self.override_hover_method:
            self.override_hover_method(self, x, y)
        else:
            pyautogui.moveTo(x, y, self.MOUSE_MOVE_SPEED)

        if self.hover_callback:
            self.hover_callback(self, x, y)

    def click(self, pad=(0, 0, 0, 0)):
        """Method to click a random point within the region. If an
        override_click_method exists, it will be used instead of the default
        pyautogui moveTo and click methods. If a click_callback is specified,
        it will be called after the click action.

        Args:
            pad (tuple, optional): Tuple specifying the offset of
                click area. The order is (x1, y1, x2, y2)
                Defaults to (0, 0, 0, 0).
        """
        x = randint(self.x + pad[0], self.x + self.w + pad[2])
        y = randint(self.y + pad[1], self.y + self.h + pad[3])

        if self.override_click_method:
            self.override_click_method(self, x, y, pad)
        else:
            pyautogui.moveTo(x, y, self.MOUSE_MOVE_SPEED)
            pyautogui.click()

        if self.click_callback:
            self.click_callback(self, x, y)

    def scroll(self, pad=(0, 0, 0, 0), *, direction, amount=1):
        """Method to scroll at a random point within the region. If an
        override_scroll_method exists, it will be used instead of the default
        pyautogui moveTo and scroll methods.

        Args:
            pad (tuple, optional): Tuple specifying the offset of
                scroll area. The order is (x1, y1, x2, y2)
                Defaults to (0, 0, 0, 0).
            direction (ScrollDirectionEnum): Scroll direction.
            amount (int, optional): Number of scroll steps to perform.
        """
        x = randint(self.x + pad[0], self.x + self.w + pad[2])
        y = randint(self.y + pad[1], self.y + self.h + pad[3])

        if self.override_scroll_method:
            self.override_scroll_method(self, x, y, pad, direction, amount)
            return

        pyautogui.moveTo(x, y, self.MOUSE_MOVE_SPEED)

        if amount < 1:
            raise ValueError(f"Unsupported scroll amount: {amount}")

        if direction is ScrollDirectionEnum.UP:
            pyautogui.scroll(amount)
        elif direction is ScrollDirectionEnum.DOWN:
            pyautogui.scroll(-amount)
        else:
            raise ValueError(f"Unsupported scroll direction: {direction}")

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
        if x is None and y is None and w is None and h is None and Region.default_bounds is not None:
            self.x, self.y, self.w, self.h = Region.default_bounds
        elif x is None and y is None and w is None and h is None:
            with mss.mss() as sct:
                screen = sct.monitors[0]
            self.x = screen["left"]
            self.y = screen["top"]
            self.w = screen["width"]
            self.h = screen["height"]
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
