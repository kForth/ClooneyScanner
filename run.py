import sys
from PyQt5 import QtWidgets, QtGui
from ui import MainWindow

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('img/icon.png'))
    window = MainWindow()
    sys.exit(app.exec_())
