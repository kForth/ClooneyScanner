import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QStyleFactory

from views import MainWindow

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('img/icon.png'))

    app.setStyle(QStyleFactory.create('fusion'))

    window = MainWindow()
    sys.exit(app.exec_())
