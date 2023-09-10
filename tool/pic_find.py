import cv2
import numpy as np

def find_subimage(image, subimage):
    # Load the images in grayscale
    image_gray = cv2.imread(image, cv2.IMREAD_GRAYSCALE)
    subimage_gray = cv2.imread(subimage, cv2.IMREAD_GRAYSCALE)

    # Perform template matching
    result = cv2.matchTemplate(image_gray, subimage_gray, cv2.TM_CCOEFF_NORMED)

    # Get the maximum value from the result matrix
    (_, max_val, _, _) = cv2.minMaxLoc(result)

    # Check if the maximum value is above a certain threshold
    threshold = 0.8
    if max_val >= threshold:
        return True
    else:
        return False

# Example usage
image = 'a.png'
subimage = 'b.png'
if find_subimage(image, subimage):
    print(f"{subimage} is a sub-image of {image}")
else:
    print(f"{subimage} is not a sub-image of {image}")