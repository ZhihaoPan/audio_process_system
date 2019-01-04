import sys
from PyQt5.QtWidgets import QApplication,QDialog,QLineEdit,QMessageBox,QFileDialog
from demo.demoD import Ui_Dialog

class dialogDemo(QDialog,Ui_Dialog):
    def __init__(self,parent=None):
        super(dialogDemo,self).__init__()
        self.setupUi(self)
        #创建事件和函数之间的连接
        self.pushButton.clicked.connect(self.getfile)
        self.pushButton_2.clicked.connect(self.confirm)

    def getfile(self):
        fileName1, filetype = QFileDialog.getOpenFileName(self, "选取文件", "./",
                                                          "All Files (*);;WAVE Files (*.wav)")  # 设置文件扩展名过滤,注意用双分号间隔
        self.lineEdit.setText(fileName1)
    def confirm(self):
        pass


if __name__=="__main__":
    app=QApplication(sys.argv)
    Qlogin=dialogDemo()
    Qlogin.show()
    sys.exit(app.exec_())