import sys
from loginpkg.dialogLogin import *
from PyQt5.QtWidgets import QApplication,QMainWindow,QDialog


if __name__=="__main__":
    app = QApplication(sys.argv)
    Qlogin = dialogLogin()
    Qlogin.show()
    sys.exit(app.exec_())
