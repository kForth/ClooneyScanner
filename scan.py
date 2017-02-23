import cv2
import numpy as np


SHEET_WIDTH = 8.5  # 8.375
SHEET_HEIGHT = 11  # 10.875


class Scanner(object):
    def __init__(self, scan_settings):
        self.scan_settings = scan_settings
        self.outline_colour = (0, 255, 0)  # BGR
        self.marker_colour = (0, 0, 235)  # BGR

    def scan_sheet(self, image):
        scan_area = self.crop_scan_area(image)

        show_sheet(scan_area)
        for field in self.scan_settings:
            print(field)

    def crop_scan_area(self, img):
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        mask_range = get_colour_mask_range(*self.marker_colour)
        mask = cv2.inRange(img_hsv, *mask_range)
        res = cv2.bitwise_and(img, img, mask=mask)

        edged = cv2.Canny(res, 100, 200)
        edged = cv2.blur(edged, (5, 5))

        (_, contours, _) = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        boxes = []

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                boxes += [approx]

        x_coords = []
        y_coords = []
        for box in boxes:
            for point in box:
                x_coords.append(point[0][0])
                y_coords.append(point[0][1])

        upper_left_corner = (min(x_coords), min(y_coords))
        lower_right_corner = (int(max(x_coords)), max(y_coords))
        cropped_img = img[upper_left_corner[1]:lower_right_corner[1], upper_left_corner[0]:lower_right_corner[0]]
        return cropped_img


def get_colour_mask_range(*rgb):
    target_colour = np.uint8([[rgb]])
    target_hsv = cv2.cvtColor(target_colour, cv2.COLOR_BGR2HSV)[0][0]
    lower_bound = np.array([0 if target_hsv[0] < 10 else target_hsv[0] - 10, 150, 150])
    upper_bound = np.array([255 if target_hsv[0] > 244 else target_hsv[0] + 10, 255, 255])
    return lower_bound, upper_bound


def show_sheet(img):
    cv2.imshow("", cv2.resize(img, (425, 550)))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    scan = Scanner({})
    scan.scan_sheet(cv2.imread('scans/sheet20170223_15081074.jpg'))
