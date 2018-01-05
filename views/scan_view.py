import glob
import json
import shutil

import cv2
import numpy as np
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import requests

from scan import Scanner
from views.edit_view import EditView


class ScanView(QMainWindow):
    def __init__(self, event_id, data_file, config_file, fields_file, scan_dirpath, clooney_host):
        # noinspection PyArgumentList
        QMainWindow.__init__(self)
        uic.loadUi('qt/ScanView.ui', self)

        self.clooney_host = clooney_host
        self.last_data = []

        self.data_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        self.scan_preview.setScaledContents(True)

        self.submit_button.clicked.connect(self.submit_scan)
        self.reject_button.clicked.connect(self.reject_scan)
        self.go_back_button.clicked.connect(self.load_last_sheet)

        self.refresh_button.clicked.connect(self.look_for_scan)
        self.fix_sheet_button.clicked.connect(self.select_corners_window)

        self.event_id = event_id
        self.data_file = data_file
        self.config = config_file
        self.fields_file = fields_file
        self.scan_dir = scan_dirpath

        for sub_folder in ["Processed", "Rejected", "Marked", "images"]:
            if not os.path.isdir(self.scan_dir + sub_folder + "/"):
                os.makedirs(self.scan_dir + sub_folder + "/")

        self.fields = dict(zip(map(lambda x: x['id'], self.fields_file), self.fields_file))

        self.scanner = Scanner(self.fields_file, self.config, self.scan_dir + "images/")

        self.entry_id = None
        self.img = None
        self.filename = ""
        self.data_types = {}

        self.get_new_scan()

        self.show()

    def enable_buttons(self, enabled=('submit', 'reject', 'go_back', 'refresh', 'fix')):
        self.submit_button.setEnabled('submit' in enabled)
        self.reject_button.setEnabled('reject' in enabled)
        self.go_back_button.setEnabled('go_back' in enabled)
        self.refresh_button.setEnabled('refresh' in enabled)
        self.fix_sheet_button.setEnabled('fix' in enabled)

    def select_corners_window(self):
        EditView(self.scan_dir, self.filename, lambda: self.look_for_scan())

    def submit_scan(self):
        if self.img is None:
            return
        self.enable_buttons([])
        edited_data = {}
        for r in range(self.data_preview.model().rowCount()):
            key = self.data_preview.model().index(r, 0).data()
            # if key in self.fields.keys() and self.fields[key]['type'] in ['HorizontalOptions', 'Boolean']:
            #     value = self.data_preview.cellWidget(r, 1).currentText()
            # else:
            value = self.data_preview.model().index(r, 1).data()
            data_type = self.data_types[key]
            data_type_name = data_type.__name__
            edited_data[key] = eval(data_type_name + "('" + value + "')", {"__builtins__": {data_type_name: data_type}})
            edited_data["filename"] = self.filename

        try:
            data = json.load(self.data_file)
        except:
            data = []

        data.append(edited_data)
        json.dump(data, self.data_file)

        data = {
            'filename': self.filename,
            'data': edited_data,
            'team': int(edited_data["team_number"]),
            'match': int(edited_data["match"]),
            'pos': int(edited_data["pos"]),
            'event': self.event_id
        }

        try:
            if self.entry_id is None:
                data['id'] = self.entry_id
            entry_id = requests.post('http://' + self.clooney_host + '/api/sql/add_entry', json=data)
            self.last_data.append({'id': entry_id, 'data': data})
        except Exception as ex:
            self.last_data.append({'id': 0, 'data': data})
            print(ex)

        shutil.move(self.scan_dir + self.filename, self.scan_dir + "Processed/" + self.filename)
        cv2.imwrite(self.scan_dir + "Marked/" + self.filename, self.img)
        self.get_new_scan()
        self.enable_buttons()

    def reject_scan(self):
        if self.img is None:
            return
        shutil.move(self.scan_dir + self.filename, self.scan_dir + "Rejected/" + self.filename)
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
            # if key in self.fields.keys() and self.fields[key]['type'] in ['HorizontalOptions', 'Boolean']:
            #     c = QComboBox()
            #     if self.fields[key]['type'] == 'Boolean':
            #         options = [1, 0]
            #     else:
            #         options = list(map(lambda x: x[0], self.fields[key]['options']['options'])) + ['']
            #     c.addItems(options)
            #     c.setCurrentIndex(options.index(data[key]))
            #     self.data_preview.setCellWidget(r, 1, c)
            # else:
            self.data_preview.setItem(r, 1, QTableWidgetItem(str(data[key])))

    def look_for_scan(self):
        self.set_buttons_enabled(False)
        self.update()
        self.get_new_scan()
        self.set_buttons_enabled(True)

    def set_buttons_enabled(self, enabled):
        self.submit_button.setEnabled(enabled)
        self.reject_button.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)
        self.fix_sheet_button.setEnabled(enabled)

    def load_last_sheet(self):
        if self.last_data:
            info = self.last_data[-1]
            self.last_data = self.last_data[:-1]
            self.entry_id = info['id']
            self.filename = info['data']['filename']
            shutil.move(self.scan_dir + "Processed/" + self.filename, self.scan_dir + self.filename)
            self.set_data(info['data']['data'])
            self.set_img(cv2.imread(self.scan_dir + "Marked/" + self.filename))
            self.filepath_label.setText(self.filename)
            self.set_buttons_enabled(True)

            try:
                data = json.load(self.data_file)
            except:
                data = []
            data.append("Undo Last Submit")
            json.dump(data, self.data_file)

    def get_new_scan(self):
        self.set_buttons_enabled(False)
        try:
            self.entry_id = None
            files = glob.glob(self.scan_dir + "*jpg") + glob.glob(self.scan_dir + "*.png")
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
