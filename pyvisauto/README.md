# pyvisauto

**pyvisauto** is a Python visual automation tool. Inspired by Sikuli, pyvisauto provides Python-native easy-to-use abstractions for complex interactions with on-screen visual elements by wrapping [OpenCV](https://opencv.org/) (specifically [opencv-contrib-python-headless](https://pypi.org/project/opencv-contrib-python-headless/)), [pyautogui](https://github.com/asweigart/pyautogui), [pytesseract](https://pypi.org/project/pytesseract/), and [numpy](https://numpy.org/).

Features include:

* OpenCV and numpy-driven image matching of on-screen elements
* TesseractOCR support
* Methods to find an image match (`find`), find all matches (`find_all`), check if a match exists (`exists`), wait until an image match occurs (`wait`), and wait for an image match to disappear (`wait_vanish`)
* Methods to click and hover over regions and matches (`click` and `hover`, respectively) with random x and y coordinates within the region
* Sub-region and cached matching for faster performance
* Method to save screenshots of matches and regions to a file (`screenshot`)

## Requirements

pyvisauto has been tested on Python 3.7. The `opencv-contrib-python-headless` package limits availability to Python 2.7 and 3.4 ~ 3.7. While pyvisauto should be compatible with Python 3, **Python 3.8 is currently not supported.**

## Installation and Usage

1. Install OS-specific dependencies:
    * Windows: No extra dependencies needed
    * Linux: `python3-xlib`
    * OSX: `pyobjc-core` and `pyobjc`, in that order
2. Install pyvisauto using pip: `pip install pyvisauto`
3. Import pyvisauto: `import pyvisauto`
4. Read the Quick Start and API docs

## Quick Start

* Define a full-screen region and assign it to `r`:

    ```
    r = pyvisauto.Region()
    ```

* Define a region with the upper-left corner at x: 50px and y: 100px, with a width of 500px and height of 300px and assign it to `r`:

    ```
    r = pyvisauto.Region(50, 100, 500, 300)
    ```

* Find the image `asset1.png` in the defined region, with a similarity score of 0.9:

    ```
    match1 = r.find('asset1.png', 0.8)
    ```

* If there has been no visual changes in the defined region, subsequent `find` actions can be expedited by passing in `cached=True`:

    ```
    match2 = r.find('asset2.png', 0.9, cached=True)
    ```

* `find_all` and `exists` can be used in a similar fashion as `find`.

* Hover over a random point in the first returned match:

    ```
    match1.hover()
    ```

* Click a random point in the second returned match:

    ```
    match2.click()
    ```

* One can use `wait` and `vanish` to wait for on-screen changes, detected by the presence or disappearance of an image on-screen, respectively:

    ```
    r.wait('wait_asset1.png', 30, 0.8)
    ```

    The above code will wait for `wait_asset1.png` in the previously defined region `r`, with a minimum similarity score of 0.8, waiting a maximum of 30 seconds before throwing a `FindFailed` exception. `vanish`, on the other hand, throws a `VanishFailed` exception. Both exceptions are defined in the `pyvisauto` module.
