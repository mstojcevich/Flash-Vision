import sys

from PyQt4 import QtGui

from imagewindow import ImageWindow
from object import Obj
from valueconfig import ValueConfig


app = QtGui.QApplication(sys.argv)

obj = Obj("conf/object.json")  # TODO maybe always send the client's to the server so there's no confusing mismatch
conf = ValueConfig("conf/values.json")  # TODO see above ^
img_window = ImageWindow(obj, conf)

sys.exit(app.exec_())