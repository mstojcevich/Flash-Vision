import sys

from PyQt4 import QtGui

from imagewindow import ImageWindow
from object import Obj
from config import Config


app = QtGui.QApplication(sys.argv)

obj = Obj(38.1, 30.48)  # Values are measured from the yellow tote
conf = Config()
img_window = ImageWindow(obj, conf)

sys.exit(app.exec_())