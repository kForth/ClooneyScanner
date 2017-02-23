from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2

from scanner import scan_sheet


class ScannerWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        uic.loadUi('qt/ScanView.ui', self)

        self.get_new_scan()

        cvImage = cv2.imread('scans/Steamworks_rev2.png')
        height, width, channels = cvImage.shape
        cvImage = cv2.cvtColor(cvImage, cv2.COLOR_BGR2RGB)
        mQImage = QImage(cvImage.data, width, height, width*3, QImage.Format_RGB888)
        self.scan_preview.setPixmap(QPixmap.fromImage(mQImage))
        self.scan_preview.setScaledContents(True)

        self.data_preview.setRowCount(4)
        self.data_preview.setColumnCount(2)

        # set data
        self.data_preview.setItem(0,0, QTableWidgetItem("Item (1,1)"))
        self.data_preview.setItem(0,1, QTableWidgetItem("Item (1,2)"))
        self.data_preview.setItem(1,0, QTableWidgetItem("Item (2,1)"))
        self.data_preview.setItem(1,1, QTableWidgetItem("Item (2,2)"))
        self.data_preview.setItem(2,0, QTableWidgetItem("Item (3,1)"))
        self.data_preview.setItem(2,1, QTableWidgetItem("Item (3,2)"))
        self.data_preview.setItem(3,0, QTableWidgetItem("Item (4,1)"))
        self.data_preview.setItem(3,1, QTableWidgetItem("Item (4,2)"))


        self.submit_button.clicked.connect(self.submit_scan)
        self.reject_button.clicked.connect(self.reject_scan)

        # self.scan_preview

        self.show()

    def submit_scan(self):
        print("Accept")

    def reject_scan(self):
        print("Reject")

    def get_new_scan(self):
        filename = "scans/Steamworks_rev2.png"
        pass
