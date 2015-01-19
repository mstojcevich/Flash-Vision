from PyQt4 import QtCore, QtGui, uic
from SimpleCV import *
import numpy
import cv2

import imgproc


def receive_all(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)
    return buf


# TODO move this to a qthelper file?
def scv_to_pixmap(scvimg, width, height):
    bitmapstr = scvimg.getBitmap().tostring()
    qimg = QtGui.QImage(bitmapstr, scvimg.width, scvimg.height, 3 * scvimg.width, QtGui.QImage.Format_RGB888)
    pixmap = QtGui.QPixmap()
    pixmap.convertFromImage(qimg.rgbSwapped())
    pixmap = pixmap.scaled(width, height, 1)
    return pixmap


class ImageWindow(QtGui.QMainWindow):
    def __init__(self, obj, config):
        """
        :param obj: Object we're tracking
        :param config: Config to set defaults from and save to
        """
        super(ImageWindow, self).__init__()

        # Set default properties
        self.raw_img = None

        # Load the layout file
        uic.loadUi('res/layout/mainwindow.ui', self)

        # Set argument properties
        self.config = config
        self.obj = obj

        # Set properties of the window
        self.setFixedSize(self.width(), self.height())
        self.setWindowTitle('Vision Preview')

        # Connect all of the sliders to their onSet methods
        min_hue_slider = self.findChild(QtGui.QSlider, 'minHueSlider')
        self.connect(min_hue_slider, QtCore.SIGNAL("valueChanged(int)"), self.min_hue_changed)
        max_hue_slider = self.findChild(QtGui.QSlider, 'maxHueSlider')
        self.connect(max_hue_slider, QtCore.SIGNAL("valueChanged(int)"), self.max_hue_changed)
        min_sat_slider = self.findChild(QtGui.QSlider, 'minSatSlider')
        self.connect(min_sat_slider, QtCore.SIGNAL("valueChanged(int)"), self.min_sat_changed)
        max_sat_slider = self.findChild(QtGui.QSlider, 'maxSatSlider')
        self.connect(max_sat_slider, QtCore.SIGNAL("valueChanged(int)"), self.max_sat_changed)
        min_val_slider = self.findChild(QtGui.QSlider, 'minValSlider')
        self.connect(min_val_slider, QtCore.SIGNAL("valueChanged(int)"), self.min_val_changed)
        max_val_slider = self.findChild(QtGui.QSlider, 'maxValSlider')
        self.connect(max_val_slider, QtCore.SIGNAL("valueChanged(int)"), self.max_val_changed)

        self.get_image_button = self.findChild(QtGui.QPushButton, 'grabImageBtn')
        def on_button_click():
            try:
                self.get_new_raw()
            except socket.error:
                QtGui.QMessageBox.warning(self, 'Connection error', 'No server running on defined IP')
        self.get_image_button.clicked.connect(on_button_click)

        self.raw_image_label = self.findChild(QtGui.QLabel, 'rawImage')
        self.processed_image_label = self.findChild(QtGui.QLabel, 'processedImage')

        self.ip_addr_box = self.findChild(QtGui.QLineEdit, 'ipTextBox')

        self.logo = self.findChild(QtGui.QLabel, 'lightningLogo')
        logo_pixmap = QtGui.QPixmap('res/img/logo.png')
        self.logo.setPixmap(logo_pixmap)

        try:
            self.get_new_raw()
        except socket.error:
            QtGui.QMessageBox.warning(self, 'Connection error', 'No server running on default IP')

        self.show()

    def get_new_raw(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.get_ip_addr(), 8621))  # TODO allow user-defined port (maybe)
        s.send('GETIMG')  # We want a raw image from the camera
        length = receive_all(s, 16)
        img_received = receive_all(s, int(length))
        s.close()  # We got what we want, let's get the hell out

        # Turn the received data back into a numpy array
        jpeg_numpy = numpy.fromstring(img_received, dtype='uint8')
        # Decode the jpeg image that was sent
        decoded_img = cv2.imdecode(jpeg_numpy, 1)
        # Turn the OpenCV image to a SimpleCV image
        self.raw_img = Image(decoded_img, cv2image=True)
        # Turn the SimpleCV image to a QT pixmap
        pixmap = scv_to_pixmap(self.raw_img, self.raw_image_label.width(), self.raw_image_label.height())
        # Set the raw image on the GUI to the new image
        self.raw_image_label.setPixmap(pixmap)
        # Run processing on the new image
        self.process_image()

    def process_image(self):
        procsvimg = imgproc.process_image(self.obj, self.raw_img, self.config)
        pixmap = scv_to_pixmap(procsvimg, self.raw_image_label.width(), self.raw_image_label.height())
        self.processed_image_label.setPixmap(pixmap)

    def min_hue_changed(self, value):
        self.config.min_hue = value
        self.process_image()

    def max_hue_changed(self, value):
        self.config.max_hue = value
        self.process_image()

    def min_sat_changed(self, value):
        self.config.min_sat = value
        self.process_image()

    def max_sat_changed(self, value):
        self.config.max_sat = value
        self.process_image()

    def min_val_changed(self, value):
        self.config.min_val = value
        self.process_image()

    def max_val_changed(self, value):
        self.config.max_val = value
        self.process_image()

    def get_ip_addr(self):
        default_ip = 'localhost'
        ip = str(self.ip_addr_box.text()).strip()
        if ' ' in ip or len(ip) is 0:  # If a space is in the input or the input is blank
            return default_ip
        return ip