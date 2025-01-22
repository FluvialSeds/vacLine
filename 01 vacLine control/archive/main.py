import os
from sys import argv, exit
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon #
from MainWindow import WidgetMain

basedir = os.path.dirname(__file__)

if __name__ == '__main__':
    
    #tell the program which application
    app = QApplication(argv)
    app.setWindowIcon(QIcon(os.path.join(basedir,'resources/aTroisIcon.ico'))) #

    #load the .ui file
    widget = WidgetMain(os.path.join(basedir,'MainUI.ui'))

    #show the app and exit when window closes
    widget.show()
    exit(app.exec_())
