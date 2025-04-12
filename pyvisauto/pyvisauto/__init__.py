import cv2
import numpy as np
import pyautogui
import pytesseract
from abc import ABC
from datetime import datetime
from random import randint
from time import sleep


# disable pyautogui failsafe when mouse moves to corner of screen
pyautogui.FAILSAFE = False


class ImageMatch(ABC):
    """Abstract base class for both Region and Match classes. Ensures that
    convenience variables and methods are shared between the two classes.
    """

    # path to tesseract if it does not exist in the path
    TESSERACT_PATH = ''
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
    # assign the callback method for click to this class variable. Should
    # accept the parameters (region, x, y)
    click_callback = None

    _captured = None

    def _capture(self):
        """Private method for capturing the defined region.

        Returns:
            PIL.Image: object representating captured region.
        """
        return pyautogui.screenshot(region=(self.x, self.y, self.w, self.h))

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
            capture = self._capture()
            capture_rgb = np.array(capture)
            self._captured = cv2.cvtColor(capture_rgb, cv2.COLOR_BGR2GRAY)

        return cv2.matchTemplate(
            self._captured, template, cv2.TM_CCOEFF_NORMED)

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
            target, self.x + max_loc[0], self.y + max_loc[1], len(template[0]),
            len(template), max_val)

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
            match_list.append(Match(
                target, self.x + match[0], self.y + match[1], len(template[0]),
                len(template), matches[match[1]][match[0]]))
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
            f"{target} not found in {self} after waiting for {wait} seconds.")

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
            f"{target} still in {self} after waiting for {wait} seconds.")

    def hover(self):
        """Method to hover over a random point within the region. If an
        override_hover_method exists, it will be used instead of the default
        pyautogui moveTo method. If a hover_callback is specified, it will be
        called after the hover action.
        """
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
            pad (tuple, optional): Tuple specifying how to modify the valid
                click area. Directions are ordered CSS-style (top, right,
                bottom, left). Positive values expand the valid click area,
                while negative values constrict it. Defaults to (0, 0, 0, 0).
        """
        x = randint(self.x - pad[3], self.x + self.w + pad[1])
        y = randint(self.y - pad[0], self.y + self.h + pad[2])

        if self.override_click_method:
            self.override_click_method(self, x, y, pad)
        else:
            pyautogui.moveTo(x, y, self.MOUSE_MOVE_SPEED)
            pyautogui.click()

        if self.click_callback:
            self.click_callback(self, x, y)
            
    def drag(self, pad=(0, 0, 0, 0)):
        """Method to drag from A to B with random point within the region. If an
        override_click_method exists, it will be used instead of the default
        pyautogui moveTo and click methods. If a click_callback is specified,
        it will be called after the click action.

        Args:
            pad (tuple, optional): Tuple specifying how to modify the valid
                click area. Directions are ordered CSS-style (top, right,
                bottom, left). Positive values expand the valid click area,
                while negative values constrict it. Defaults to (0, 0, 0, 0).
        """
        x = randint(self.x - pad[3], self.x + self.w + pad[1])
        y = randint(self.y - pad[0], self.y + self.h + pad[2])

        pyautogui.dragTo(x, y, self.MOUSE_MOVE_SPEED, button='left')

        if self.click_callback:
            self.click_callback(self, x, y)

    def ocr(self, lang, config):
        """Method for running Optical Character Recognition (OCR) on the region
        using TesseractOCR. Tesseract must be installed separately and
        available in your path, or the path to it must be specified in the
        ImageMatch.TESSERACT_PATH class variable.

        Args:
            lang (str): language to OCR for (see pytesseract docs).
            config (str): pytesseract config for OCR (see pytesseract docs).

        Raises:
            Exception: raised when tesseract is not available.

        Returns:
            str: result of OCR attempt.
        """
        pytesseract.pytesseract.tesseract_cmd = self.TESSERACT_PATH
        capture = self._capture()
        try:
            return pytesseract.image_to_string(
                capture, lang=lang, config=config)
        except pytesseract.pytesseract.TesseractNotFoundError:
            raise Exception(
                "tesseract is not installed or it's not in your path, "
                "or you've not specified the path to tesseract in "
                "ImageMatch.TESSERACT_PATH")

    def save_screenshot(self, filename):
        """Method for saving a screenshot of the region to a file.

        Args:
            filename (str): path to save screenshot to.
        """
        capture = self._capture()
        capture.save(filename)


class Region(ImageMatch):
    """Class used to define a (search) region. Create a Region to visually
    search within it or to use other ImageMatch public methods.
    """
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
        if x is None and y is None and w is None and h is None:
            screen = pyautogui.size()
            self.x = 0
            self.y = 0
            self.w = screen.width
            self.h = screen.height
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
            f"{self.similarity:.5f} ]")


class FindFailed(Exception):
    """Raised when an asset could not be found on screen.
    """
    pass


class VanishFailed(Exception):
    """Raised when an asset expected to disappear does not disappear by the
    timeout time.
    """
    pass
