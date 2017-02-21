from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class ScannerWindow(QMainWindow):
    def __init__(self):
        super(ScannerWindow, self).__init__()
        uic.loadUi('qt/ScanView.ui', self)

        self.scan_preview.setPixmap(QPixmap('scans/t5406_m60_p5.jpg'))
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
