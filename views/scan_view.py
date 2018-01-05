import glob
import json
import shutil
import os

import cv2
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import requests

from runners import Runner
from scanners import LegacyScanner


class ScanView(QMainWindow):

    def __init__(self, event_id, data_file, config_file, fields_file, scan_dirpath, clooney_host):
        super().__init__()
        uic.loadUi('ui/ScanView.ui', self)

        self.clooney_host = clooney_host
        self.data_history = []

        self.data_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        self.scan_preview.setScaledContents(True)
        self.scan_preview.mousePressEvent = self.handle_img_click

        self.click_mode = ""
        self.corners = []

        self.submit_button.clicked.connect(self.submit_scan)
        self.reject_button.clicked.connect(self.reject_scan)
        self.go_back_button.clicked.connect(self.load_last_sheet)

        self.refresh_button.clicked.connect(self.look_for_scan)

        self.four_corners_button.clicked.connect(self.handle_four_corners_button)
        self.rotate_180_button.clicked.connect(self.handle_rotate_180_button)
        self.toggle_view_button.clicked.connect(self.handle_toggle_view_button)

        self.event_id = event_id
        self.data_filepath = data_file
        self.config = config_file
        self.fields_file = fields_file
        self.scan_dir = scan_dirpath

        for sub_folder in ["Processed", "Rejected", "Marked", "images"]:
            if not os.path.isdir(self.scan_dir + sub_folder + "/"):
                os.makedirs(self.scan_dir + sub_folder + "/")

        self.fields = dict(zip(map(lambda x: x['id'], self.fields_file), self.fields_file))

        self.scanner = LegacyScanner(self.fields_file, self.config, self.scan_dir + "images/")

        self.backup_img = np.zeros((1, 1, 3), np.uint8)
        self.img = np.zeros((1, 1, 3), np.uint8)
        self.raw_img = np.zeros((1, 1, 3), np.uint8)
        self.selected_img = "img"
        self.filename = ""
        self.data_types = {}

        self.get_new_scan()

        self.show()

    def enable_inputs(self, enabled=('submit', 'reject', 'go_back', 'refresh', 'four', 'rotate', 'toggle', 'data')):
        self.submit_button.setEnabled('submit' in enabled)
        self.reject_button.setEnabled('reject' in enabled)
        self.go_back_button.setEnabled('go_back' in enabled)
        self.refresh_button.setEnabled('refresh' in enabled)
        self.four_corners_button.setEnabled('four' in enabled)
        self.rotate_180_button.setEnabled('rotate' in enabled)
        self.toggle_view_button.setEnabled('toggle' in enabled)
        self.data_preview.setEnabled('data' in enabled)

    def handle_img_click(self, event):
        if self.click_mode == "four_corners":
            img_h, img_w = self.raw_img.shape[:-1]
            w_scale = img_w / self.scan_preview.size().width()
            h_scale = img_h / self.scan_preview.size().height()
            point = tuple(map(int, (event.x() * w_scale, event.y() * h_scale)))
            self.corners.append(point)
            if len(self.corners) == 4:
                selected_points = sorted(self.corners, key=lambda l: sum(l))
                new_points = ((200, 200), (img_w - 200, 200), (200, img_h - 200), (img_w - 200, img_h - 200))
                new_points = sorted(new_points, key=lambda e: sum(e))
                warp_matrix = cv2.getPerspectiveTransform(np.float32(selected_points), np.float32(new_points))
                self.raw_img = cv2.warpPerspective(self.raw_img, warp_matrix, (img_w, img_h))
                self.reset_click_mode()
                self.get_new_scan(self.raw_img)

    def handle_toggle_view_button(self):
        if self.selected_img == 'img':
            self.selected_img = 'raw'
            self.set_img(self.raw_img)
        else:
            self.selected_img = 'img'
            self.set_img(self.img)

    def handle_four_corners_button(self):
        if self.click_mode == "four_corners":
            self.reset_click_mode()
        else:
            self.selected_img = 'raw'
            self.set_img(self.raw_img)
            self.enable_inputs('four')
            self.corners = []
            self.scan_preview.setCursor(Qt.PointingHandCursor)
            self.click_mode = "four_corners"

    def handle_rotate_180_button(self):
        img_h, img_w = self.img.shape[:-1]
        warp_matrix = cv2.getRotationMatrix2D((img_w / 2, img_h / 2), 180, 1)
        img = self.img.copy()
        img = cv2.warpAffine(img, warp_matrix, (img_w, img_h), cv2.INTER_LINEAR)
        self.img = img
        self.set_img(img)
        self.reset_click_mode()

    def reset_click_mode(self):
        self.scan_preview.setCursor(Qt.ArrowCursor)
        self.enable_inputs()
        self.click_mode = ""
        self.corners = []
        self.set_img(self.img)
        self.selected_img = 'img'

    def submit_scan(self):
        if self.img is None:
            return
        self.enable_inputs([])

        edited_data = {}
        for r in range(self.data_preview.model().rowCount()):
            key = self.data_preview.model().index(r, 0).data()
            if key in self.fields.keys() and self.fields[key]['type'] in ['HorizontalOptions', 'Boolean']:
                value = self.data_preview.cellWidget(r, 1).currentText()
            elif key in ['pos']:
                value = self.data_preview.cellWidget(r, 1).currentText()
                value = self.scanner.POSITIONS.index(value)
            else:
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
        json.dump(data, open(self.data_filepath, "w+"))

        data = {
            'filename': self.filename,
            'data': edited_data,
            'team': int(edited_data["team_number"]),
            'match': int(edited_data["match"]),
            'pos': int(edited_data["pos"]),
            'event': self.event_id
        }

        def post_func():
            try:
                requests.post('http://' + self.clooney_host + '/api/sql/add_entry', json=data)
            except Exception as ex:
                print(ex)
        Runner(target=post_func).run()

        shutil.move(self.scan_dir + self.filename, self.scan_dir + "Processed/" + self.filename)
        cv2.imwrite(self.scan_dir + "Marked/" + self.filename, self.img)
        self.data_history.append(data)
        self.get_new_scan()
        self.enable_inputs()

    def reject_scan(self):
        if self.img is None:
            return
        shutil.move(self.scan_dir + self.filename, self.scan_dir + "Rejected/" + self.filename)
        self.get_new_scan()

    def set_img(self, cv_img):
        height, width, channels = cv_img.shape
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        q_image = QImage(cv_img.data, width, height, width * 3, QImage.Format_RGB888)
        self.scan_preview.setPixmap(QPixmap.fromImage(q_image))

    def set_data(self, data):
        self.data_types = dict(zip(data.keys(), map(type, data.values())))
        self.data_preview.setRowCount(len(data))

        for r in range(len(data)):
            key = list(data.keys())[r]
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & Qt.ItemIsEditable)
            self.data_preview.setItem(r, 0, key_item)
            if key in self.fields.keys() and self.fields[key]['type'] in ['HorizontalOptions', 'Boolean']:
                c = QComboBox()
                if self.fields[key]['type'] == 'Boolean':
                    options = [1, 0]
                else:
                    options = list(map(lambda x: x[0], self.fields[key]['options']['options'])) + ['']
                c.addItems(map(str, options))
                c.setCurrentIndex(options.index(data[key]))
                self.data_preview.setCellWidget(r, 1, c)
            elif key in ['pos']:
                c = QComboBox()
                c.addItems(self.scanner.POSITIONS)
                if data[key] >= len(self.scanner.POSITIONS):
                    c.setCurrentIndex(0)
                c.setCurrentIndex(data[key])
                self.data_preview.setCellWidget(r, 1, c)
            else:
                self.data_preview.setItem(r, 1, QTableWidgetItem(str(data[key])))

    def look_for_scan(self):
        self.enable_inputs([])
        self.update()
        self.get_new_scan()
        self.enable_inputs()

    def load_last_sheet(self):
        if self.data_history:
            info = self.data_history[-1]
            self.data_history = self.data_history[:-1]
            self.filename = info['data']['filename']
            shutil.move(self.scan_dir + "Processed/" + self.filename, self.scan_dir + self.filename)
            self.set_data(info['data']['data'])
            self.set_img(cv2.imread(self.scan_dir + "Marked/" + self.filename))
            self.filepath_label.setText(self.filename)
            self.enable_inputs()

            try:
                data = json.load(open(self.data_filepath))
                if data:
                    data = data[:-1]
            except:
                data = []
            json.dump(data, open(self.data_filepath, "w+"))

    def get_new_scan(self, raw_scan=None):
        self.enable_inputs([])
        if raw_scan is None:
            try:
                files = glob.glob(self.scan_dir + "*jpg") + glob.glob(self.scan_dir + "*.png")
                selected_file = files[0]
                self.filename = selected_file.split("/")[-1]
                self.filepath_label.setText(files[0])
                raw_scan = cv2.imread(selected_file)
            except Exception as ex:
                print("Failed to read img")
                self.filepath_label.setText(str(ex))
                self.set_img(np.zeros((1, 1, 3), np.uint8))
                self.set_data({})
                self.refresh_button.setEnabled(True)
                return

        self.raw_img = np.copy(raw_scan)
        data, marked_sheet = self.scanner.scan_sheet(raw_scan)

        self.img = marked_sheet
        self.set_img(self.img)
        self.set_data(data)

        self.enable_inputs()
