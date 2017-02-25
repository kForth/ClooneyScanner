import json
import glob
import shutil

import cv2
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from scan import Scanner


class ScanView(QMainWindow):
    def __init__(self, data_dirpath, config_filepath, fields_filepath, scan_dirpath):
        # noinspection PyArgumentList
        QMainWindow.__init__(self)
        uic.loadUi('qt/ScanView.ui', self)

        self.data_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        self.scan_preview.setScaledContents(True)

        self.submit_button.clicked.connect(self.submit_scan)
        self.reject_button.clicked.connect(self.reject_scan)
        self.refresh_button.clicked.connect(self.look_for_scan)

        self.data_dir = data_dirpath + "data.json"
        self.config_file = config_filepath
        self.fields_file = fields_filepath
        self.scan_dir = scan_dirpath

        fields = json.load(open(self.fields_file))
        config = json.load(open(self.config_file))
        self.scanner = Scanner(fields, config, self.data_dir + "images/")

        self.filename = ""
        self.img = None
        self.data = {}

        self.get_new_scan()

        self.show()

    def submit_scan(self):
        print("Accept")  # TODO: Actually do something with the data
        if self.img is None:
            return

        shutil.move(self.scan_dir + self.filename, self.scan_dir + "processed/" + self.filename)
        cv2.imwrite(self.scan_dir + "marked/" + self.filename, self.img)

        self.get_new_scan()

    def reject_scan(self):
        print("Reject")  # TODO: Do something with the data and sheets
        if self.img is None:
            return

        shutil.move(self.scan_dir + self.filename, self.scan_dir + "rejected/" + self.filename)
        self.get_new_scan()

    def set_img(self, cv_img):
        height, width, channels = cv_img.shape
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        q_image = QImage(cv_img.data, width, height, width * 3, QImage.Format_RGB888)
        # noinspection PyCallByClass,PyTypeChecker,PyArgumentList
        self.scan_preview.setPixmap(QPixmap.fromImage(q_image))

    def set_data(self, data):
        self.data_preview.setRowCount(len(data))

        for r in range(len(data)):
            key = list(data.keys())[r]
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & Qt.ItemIsEditable)
            self.data_preview.setItem(r, 0, key_item)
            self.data_preview.setItem(r, 1, QTableWidgetItem(str(data[key])))

    def look_for_scan(self):
        self.get_new_scan()

    def set_buttons_enabled(self, enabled):
        self.submit_button.setEnabled(enabled)
        self.reject_button.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)

    def get_new_scan(self):
        self.set_buttons_enabled(False)

        files = glob.glob(self.scan_dir + "*jpg") + glob.glob(self.scan_dir + "*.png")
        try:
            selected_file = files[0]
            self.filename = selected_file.split("/")[-1]
            raw_scan = cv2.imread(selected_file)
        except Exception as ex:
            print("Failed to read img")
            self.filepath_label.setText(str(ex))
            self.set_img(np.zeros((1, 1, 3), np.uint8))
            self.set_data({})
            self.refresh_button.setEnabled(True)
            return

        data, marked_sheet = self.scanner.scan_sheet(raw_scan)

        self.img = marked_sheet
        self.data = data
        self.set_img(self.img)
        self.set_data(self.data)
        self.filepath_label.setText(files[0])

        self.set_buttons_enabled(True)
