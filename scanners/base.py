from abc import abstractmethod

import numpy as np
import cv2


class ScannerBase(object):

    POSITIONS = ['Red 1', 'Red 2', 'Red 3', 'Blue 1', 'Blue 2', 'Blue 3']

    NUMBERS_MODEL = [[True, True, True, False, True, True, True],
                     [False, False, True, False, False, True, False],
                     [True, False, True, True, True, False, True],
                     [True, False, True, True, False, True, True],
                     [False, True, True, True, False, True, False],
                     [True, True, False, True, False, True, True],
                     [True, True, False, True, True, True, True],
                     [True, False, True, False, False, True, False],
                     [True, True, True, True, True, True, True],
                     [True, True, True, True, False, True, True]]
    ALT_NUMBERS_MODEL = [[False, False, False, False, False, False, False],
                         [False, True, False, False, True, False, False],
                         None,
                         None,
                         None,
                         None,
                         [False, True, False, True, True, True, True],
                         None,
                         None,
                         [True, True, True, True, False, True, False]]

    def __init__(self):
        pass

    @abstractmethod
    def scan_sheet(self, image):
        pass

    @staticmethod
    def _get_colour_mask_range(*rgb, sensitivity=10):
        target_colour = np.uint8([[rgb]])
        target_hsv = cv2.cvtColor(target_colour, cv2.COLOR_RGB2HSV)[0][0]
        lower_bound = np.array([0 if target_hsv[0] < sensitivity else target_hsv[0] - sensitivity, 150, 150])
        upper_bound = np.array([255 if target_hsv[0] > 255 - sensitivity else target_hsv[0] + sensitivity, 255, 255])
        return lower_bound, upper_bound

    @staticmethod
    def _round_colours(img):
        img = ((img / 255.0).round() * 255)
        return img.astype(np.uint8)

    @staticmethod
    def _show_sheet(img):
        cv2.imshow("Image", cv2.resize(img, (425, 550)))
        cv2.waitKey(0)
        cv2.destroyAllWindows()
