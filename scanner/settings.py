from PyQt5 import QtWidgets, uic

class ScannerWindow(QtWidgets.QDialog):
    def __init__(self):
        super(ScannerWindow, self).__init__()
        uic.loadUi('qt/SettingsView.ui', self)

        self.done_button.clicked.connect(self.done)

        self.show()

    def done(self):
        print("Done")
