import glob
import json
import os
import shutil

import cv2
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import requests

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

        self.data_dir = data_dirpath
        self.config_file = config_filepath
        self.fields_file = fields_filepath
        self.scan_dir = scan_dirpath
        self.check_files()

        self.config = json.load(open(self.config_file))
        self.data_filepath = data_dirpath + self.config["event"].lower().replace(" ", "_") + ".json"

        fields = json.load(open(self.fields_file))
        config = json.load(open(self.config_file))
        self.scanner = Scanner(fields, config, self.data_dir + "images/")

        self.filename = ""
        self.img = None
        self.data_types = {}

        self.get_new_scan()

        self.show()

    def check_files(self):
        if not os.path.isfile(self.data_dir):
            os.makedirs(os.path.dirname(self.data_dir), exist_ok=True)
        if not os.path.isfile(self.config_file):
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            json.dump({}, open(self.config_file, "w"))
        if not os.path.isfile(self.fields_file):
            os.makedirs(os.path.dirname(self.fields_file), exist_ok=True)
            json.dump({}, open(self.fields_file, "w"))
        if not os.path.isdir(self.scan_dir):
            os.makedirs(os.path.dirname(self.scan_dir), exist_ok=True)

    def submit_scan(self):
        if self.img is None:
            return
        edited_data = {}
        for r in range(self.data_preview.model().rowCount()):
            key = self.data_preview.model().index(r, 0).data()
            value = self.data_preview.model().index(r, 1).data()
            data_type = self.data_types[key]
            data_type_name = data_type.__name__
            edited_data[key] = eval(data_type_name + "('" + value + "')", {"__builtins__": {data_type_name: data_type}})
            edited_data["filename"] = self.filename

        try:
            data = json.load(open(self.data_filepath))
        except:
            data = []

        data.append(edited_data)
        json.dump(data, open(self.data_filepath, "w"))

        try:
            data = {
                'filename': self.filename,
                'data': edited_data,
                'team': edited_data["team_number"],
                'match': edited_data["match"],
                'pos': edited_data["pos"],
                'event': "2017onto2"  # TODO: Get this from the settings page.
            }
            requests.post('http://0.0.0.0:5000/api/sql/add_entry', json=data)
        except Exception as ex:
            print(ex)

        shutil.move(self.scan_dir + self.filename, self.scan_dir + "processed/" + self.filename)
        cv2.imwrite(self.scan_dir + "marked/" + self.filename, self.img)
        self.get_new_scan()

    def reject_scan(self):
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
        self.data_types = dict(zip(data.keys(), map(type, data.values())))
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
        self.set_img(self.img)
        self.set_data(data)
        self.filepath_label.setText(files[0])

        self.set_buttons_enabled(True)
