from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QFileDialog
from PyQt5.QtCore import QSettings

from ui.scan_view import ScanView


class MainWindow(QMainWindow):
    def __init__(self):
        # noinspection PyArgumentList
        QMainWindow.__init__(self)
        uic.loadUi('qt/MainView.ui', self)
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "KestinGoforth", "ClooneyScanner")

        self.data_dirpath.setText(self.settings.value("data_dirpath"))
        self.config_filepath.setText(self.settings.value("config_filepath"))
        self.fields_filepath.setText(self.settings.value("fields_filepath"))
        self.scans_dirpath.setText(self.settings.value("scans_dirpath"))

        self.data_dirpath_button.clicked.connect(self.select_data_dir)
        self.config_filepath_button.clicked.connect(self.select_config_file)
        self.fields_filepath_button.clicked.connect(self.select_fields_file)
        self.scans_dirpath_button.clicked.connect(self.select_scan_dir)

        self.start_scanning.clicked.connect(self.show_scan_view)
        self.cancel_button.clicked.connect(self.close)

        self.show()

    def show_scan_view(self):
        data_dp = self.data_dirpath.text()
        config_fp = self.config_filepath.text()
        fields_fp = self.fields_filepath.text()
        scans_dp = self.scans_dirpath.text()

        self.settings.setValue("data_dirpath", data_dp)
        self.settings.setValue("config_filepath", config_fp)
        self.settings.setValue("fields_filepath", fields_fp)
        self.settings.setValue("scans_dirpath", scans_dp)

        ScanView(data_dp, config_fp, fields_fp, scans_dp)
        self.hide()

    def select_data_dir(self):
        self.data_dirpath.setText(QFileDialog.getExistingDirectory() + "/")

    def select_config_file(self):
        self.config_filepath.setText(QFileDialog.getOpenFileName()[0])

    def select_fields_file(self):
        self.fields_filepath.setText(QFileDialog.getOpenFileName()[0])

    def select_scan_dir(self):
        self.scans_dirpath.setText(QFileDialog.getExistingDirectory() + "/")
