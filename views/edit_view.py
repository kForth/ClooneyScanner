import math

import cv2
import numpy as np
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class EditView(QMainWindow):
    def __init__(self, scan_dir: str, filename: str, callback: type(lambda x: x)):
        # noinspection PyArgumentList
        QMainWindow.__init__(self)
        uic.loadUi('qt/EditView.ui', self)

        self.scan_dir = scan_dir
        self.filename = filename
        self.callback = callback

        self.scan_preview.setScaledContents(True)
        self.scan_preview.mousePressEvent = self.handle_img_click

        self.cancel_button.clicked.connect(self.close)
        self.submit_button.clicked.connect(self.submit)
        self.vertical_line_button.clicked.connect(self.handle_vertical_line_button)
        self.four_corners_button.clicked.connect(self.handle_four_corners_button)
        self.rotate_180_button.clicked.connect(self.handle_rotate_180_button)

        self.click_mode = ""
        self.corners = []

        self.img = cv2.imread(self.scan_dir + self.filename)
        self.set_img(self.img)

        self.show()

    def submit(self):
        cv2.imwrite(self.scan_dir + self.filename, self.img)
        self.callback()
        self.close()

    def handle_img_click(self, event):
        if self.click_mode == "four_corners":
            img_h, img_w = self.img.shape[:-1]
            w_scale = img_w / 340.0
            h_scale = img_h / 440.0
            point = tuple(map(int, (event.x() * w_scale, event.y() * h_scale)))
            self.corners.append(point)
            if len(self.corners) >= 4:
                self.corners = self.corners[-4:]
                selected_points = sorted(self.corners, key=lambda l: sum(l))
                new_points = ((400, 400), (img_w - 400, 400), (400, img_h - 400), (img_w - 400, img_h - 400))
                new_points = sorted(new_points, key=lambda e: sum(e))
                warp_matrix = cv2.getPerspectiveTransform(np.float32(selected_points), np.float32(new_points))
                self.img = cv2.warpPerspective(self.img, warp_matrix, (img_w, img_h))
                self.set_img(self.img)
                self.reset_click_mode()
        elif self.click_mode == "vertical_line":
            img_h, img_w = self.img.shape[:-1]
            w_scale = img_w / 340.0
            h_scale = img_h / 440.0
            point = tuple(map(int, (event.x() * w_scale, event.y() * h_scale)))
            self.corners.append(point)
            if len(self.corners) >= 2:
                self.corners = self.corners[-2:]
                slope = (self.corners[1][0] - self.corners[0][0]) / (self.corners[1][1] - self.corners[0][1])
                angle = math.degrees(math.atan(slope))
                warp_matrix = cv2.getRotationMatrix2D((img_w / 2, img_h / 2), -angle / 2, 1)
                self.img = cv2.warpAffine(self.img, warp_matrix, (img_w, img_h), cv2.INTER_LINEAR)
                self.set_img(self.img)
                self.reset_click_mode()

    def reset_click_mode(self):
        self.setCursor(Qt.ArrowCursor)
        self.enable_buttons()
        self.click_mode = ""
        self.corners = []

    def handle_rotate_180_button(self):
        img_h, img_w = self.img.shape[:-1]
        warp_matrix = cv2.getRotationMatrix2D((img_w / 2, img_h / 2), 180, 1)
        img = self.img.copy()
        img = cv2.warpAffine(img, warp_matrix, (img_w, img_h), cv2.INTER_LINEAR)
        self.img = img
        self.set_img(img)
        self.reset_click_mode()

    def handle_four_corners_button(self):
        if self.click_mode == "four_corners":
            self.reset_click_mode()
        else:
            self.enable_buttons('corners')
            self.corners = []
            self.setCursor(Qt.CrossCursor)
            self.click_mode = "four_corners"
            self.set_img(self.img)

    def handle_vertical_line_button(self):
        if self.click_mode == "vertical_line":
            self.reset_click_mode()
        else:
            self.enable_buttons('line')
            self.corners = []
            self.setCursor(Qt.CrossCursor)
            self.click_mode = "vertical_line"
            self.set_img(self.img)

    def enable_buttons(self, enabled=('line', 'corners', 'rotate', 'submit')):
        self.vertical_line_button.setEnabled('line' in enabled)
        self.four_corners_button.setEnabled('corners' in enabled)
        self.rotate_180_button.setEnabled('rotate' in enabled)
        self.submit_button.setEnabled('submit' in enabled)

    def set_img(self, cv_img):
        height, width, channels = cv_img.shape
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        q_image = QImage(cv_img.data, width, height, width * 3, QImage.Format_RGB888)
        # noinspection PyCallByClass,PyTypeChecker,PyArgumentList
        self.scan_preview.setPixmap(QPixmap.fromImage(q_image))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication([])
    app.setWindowIcon(QIcon('img/icon.png'))
    window = EditView("../scans/", "04082017102441.jpg", lambda: print('callback'))
    sys.exit(app.exec_())
