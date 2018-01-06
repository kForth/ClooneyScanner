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

        self.data_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.data_preview.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.data_preview.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.data_preview.horizontalHeader().resizeSection(0, 160)
        self.data_preview.horizontalHeader().resizeSection(1, 160)

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
        self.current_img = np.zeros((1, 1, 3), np.uint8)
        self.selected_img = "img"
        self.filename = ""
        self.data_types = {}
        self.filepath_label_old_text = ""

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
            x = int(event.x() * w_scale)
            y = int(event.y() * h_scale)
            self.corners.append((x, y))
            cv2.rectangle(self.current_img, (x - 10, y - 10), (x+10, y+10), (0, 255, 0), thickness=10)
            self.set_img(self.current_img)
            if len(self.corners) == 4:
                selected_points = sorted(self.corners, key=lambda l: sum(l))
                new_points = ((200, 200), (img_w - 200, 200), (200, img_h - 200), (img_w - 200, img_h - 200))
                new_points = sorted(new_points, key=lambda e: sum(e))
                warp_matrix = cv2.getPerspectiveTransform(np.float32(selected_points), np.float32(new_points))
                self.raw_img = cv2.warpPerspective(self.raw_img, warp_matrix, (img_w, img_h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
                self.reset_click_mode()
                self.get_new_scan(self.raw_img)

    def handle_toggle_view_button(self):
        if self.selected_img == 'img':
            self.selected_img = 'raw'
            self.set_img(self.raw_img)
            self.current_img = np.copy(self.raw_img)
        else:
            self.selected_img = 'img'
            self.set_img(self.img)
            self.current_img = np.copy(self.img)

    def set_filepath_label_text(self, text):
        self.filepath_label_old_text = self.filepath_label.text()
        self.filepath_label.setText(text)

    def handle_four_corners_button(self):
        if self.click_mode == "four_corners":
            self.reset_click_mode()
        else:
            self.set_filepath_label_text('Click on the 4 corners of the bounding box.')
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
        self.set_filepath_label_text(self.filepath_label_old_text)
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
                value = self.data_preview.cellWidget(r, 2).currentText()
            elif key in ['pos']:
                value = self.data_preview.cellWidget(r, 2).currentText()
                if value not in self.scanner.POSITIONS:
                    self.enable_inputs()
                    return
                value = self.scanner.POSITIONS.index(value)
            else:
                value = self.data_preview.model().index(r, 2).data()
            data_type = self.data_types[key]
            data_type_name = data_type.__name__
            edited_data[key] = eval('{0}("{1}")'.format(data_type_name, value), {"__builtins__": {data_type_name: data_type}})
            edited_data["filename"] = self.filename

        if not edited_data['team_number']:
            return
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
        self.get_new_scan()
        self.enable_inputs()

    def reject_scan(self):
        if self.img is None:
            return
        shutil.move(self.scan_dir + self.filename, self.scan_dir + "Rejected/" + self.filename)
        self.get_new_scan()

    def set_img(self, cv_img):
        self.current_img = np.copy(cv_img)
        height, width, channels = cv_img.shape
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        q_image = QImage(cv_img.data, width, height, width * 3, QImage.Format_RGB888)
        self.scan_preview.setPixmap(QPixmap.fromImage(q_image))

    def set_data(self, data):
        self.data_types = dict(zip(data.keys(), map(type, data.values())))
        self.data_preview.setRowCount(len(data))

        for row in range(len(data)):
            key = list(data.keys())[row]
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & Qt.ItemIsEditable)
            if key in ['match', 'pos']:
                label_item = QTableWidgetItem(key.title())
            else:
                label_item = QTableWidgetItem(self.fields[key]['options']['label'])
            label_item.setFlags(label_item.flags() & Qt.ItemIsEditable)
            self.data_preview.setItem(row, 0, key_item)
            self.data_preview.setItem(row, 1, label_item)
            if key in self.fields.keys() and self.fields[key]['type'] in ['HorizontalOptions', 'Boolean']:
                c = QComboBox()
                if self.fields[key]['type'] == 'Boolean':
                    options = [1, 0]
                else:
                    options = list(map(lambda x: x[0], self.fields[key]['options']['options'])) + ['']
                c.addItems(map(str, options))
                c.setCurrentIndex(options.index(data[key]))
                self.data_preview.setCellWidget(row, 2, c)
            elif key in ['pos']:
                c = QComboBox()
                c.addItems(self.scanner.POSITIONS)
                if data[key] >= len(self.scanner.POSITIONS):
                    c.setCurrentIndex(0)
                c.setCurrentIndex(data[key])
                self.data_preview.setCellWidget(row, 2, c)
            else:
                self.data_preview.setItem(row, 2, QTableWidgetItem(str(data[key])))

    def look_for_scan(self):
        self.enable_inputs([])
        self.update()
        self.get_new_scan()
        self.enable_inputs()

    def load_last_sheet(self):
        try:
            data = json.load(open(self.data_filepath))
        except:
            data = []
        if data:
            info = data[-1]
            self.filename = info['filename']
            del info['filename']
            shutil.move(self.scan_dir + "Processed/" + self.filename, self.scan_dir + self.filename)
            self.set_data(info)
            self.set_img(cv2.imread(self.scan_dir + "Marked/" + self.filename))
            self.set_filepath_label_text(self.filename)
            self.enable_inputs()

            data = data[:-1]
            json.dump(data, open(self.data_filepath, "w+"))

    def get_new_scan(self, raw_scan=None):
        self.enable_inputs([])
        if raw_scan is None:
            try:
                files = glob.glob(self.scan_dir + "*jpg") + glob.glob(self.scan_dir + "*.png")
                selected_file = files[0]
                self.filename = selected_file.split("/")[-1]
                self.set_filepath_label_text(files[0])
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
