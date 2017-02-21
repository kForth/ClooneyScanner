import sys
from PyQt5 import QtWidgets, QtGui
from scanner import ScannerWindow

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('img/icon.png'))
    window = ScannerWindow()
    sys.exit(app.exec_())
