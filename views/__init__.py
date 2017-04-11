import os
import json

from PyQt5 import uic
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QFileDialog, QMainWindow

from views.scan_view import ScanView


class MainWindow(QMainWindow):
    def __init__(self):
        # noinspection PyArgumentList
        QMainWindow.__init__(self)
        uic.loadUi('qt/MainView.ui', self)
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "KestinGoforth", "ClooneyScanner")

        self.event_id_entry.setText(self.settings.value("event_id"))
        self.data_filepath.setText(self.settings.value("data_filepath"))
        self.config_filepath.setText(self.settings.value("config_filepath"))
        self.fields_filepath.setText(self.settings.value("fields_filepath"))
        self.scans_dirpath.setText(self.settings.value("scans_dirpath"))

        self.data_filepath_button.clicked.connect(self.select_data_dir)
        self.config_filepath_button.clicked.connect(self.select_config_file)
        self.fields_filepath_button.clicked.connect(self.select_fields_file)
        self.scans_dirpath_button.clicked.connect(self.select_scan_dir)

        self.start_scanning.clicked.connect(self.show_scan_view)
        self.cancel_button.clicked.connect(self.close)

        self.show()

    def show_scan_view(self):
        files = self.load_files()
        if not files:
            return
        self.settings.setValue("event_id", self.event_id_entry.text())
        self.settings.setValue("data_filepath", self.data_filepath.text())
        self.settings.setValue("config_filepath", self.config_filepath.text())
        self.settings.setValue("fields_filepath", self.fields_filepath.text())
        self.settings.setValue("scans_dirpath", self.scans_dirpath.text())

        self.scan_view = ScanView(self.event_id_entry.text(), files[0], files[1], files[2], self.scans_dirpath.text())
        self.hide()

    def select_data_dir(self):
        self.data_filepath.setText(QFileDialog.getSaveFileName(None, 'Save Data File', 'data.json', '*.json')[0])

    def select_config_file(self):
        self.config_filepath.setText(QFileDialog.getOpenFileName(None, 'Select Sheet Config File', '', '*.json')[0])

    def select_fields_file(self):
        self.fields_filepath.setText(QFileDialog.getOpenFileName(None, 'Select Fields File', '', '*.json')[0])

    def load_files(self):
        try:
            return (open(self.data_filepath.text(), "w+"),
                    json.load(open(self.config_filepath.text())),
                    json.load(open(self.fields_filepath.text())))
        except Exception as ex:
            print(ex)
            return False

    def select_scan_dir(self):
        self.scans_dirpath.setText(QFileDialog.getExistingDirectory() + "/")
        if not os.path.isdir(self.scans_dirpath.text()):
            self.data_filepath.setText("Error")
