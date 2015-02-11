from PyQt4 import QtCore, QtGui, uic
from SimpleCV import *
import numpy
import cv2
import json

import imgproc
import camprop


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
        self.min_hue_slider = self.findChild(QtGui.QSlider, 'minHueSlider')
        self.connect(self.min_hue_slider, QtCore.SIGNAL("valueChanged(int)"), self.min_hue_changed)
        self.max_hue_slider = self.findChild(QtGui.QSlider, 'maxHueSlider')
        self.connect(self.max_hue_slider, QtCore.SIGNAL("valueChanged(int)"), self.max_hue_changed)
        self.min_sat_slider = self.findChild(QtGui.QSlider, 'minSatSlider')
        self.connect(self.min_sat_slider, QtCore.SIGNAL("valueChanged(int)"), self.min_sat_changed)
        self.max_sat_slider = self.findChild(QtGui.QSlider, 'maxSatSlider')
        self.connect(self.max_sat_slider, QtCore.SIGNAL("valueChanged(int)"), self.max_sat_changed)
        self.min_val_slider = self.findChild(QtGui.QSlider, 'minValSlider')
        self.connect(self.min_val_slider, QtCore.SIGNAL("valueChanged(int)"), self.min_val_changed)
        self.max_val_slider = self.findChild(QtGui.QSlider, 'maxValSlider')
        self.connect(self.max_val_slider, QtCore.SIGNAL("valueChanged(int)"), self.max_val_changed)

        self.get_image_button = self.findChild(QtGui.QPushButton, 'grabImageBtn')
        self.get_image_button.clicked.connect(self.grab_img)
        self.send_config_button = self.findChild(QtGui.QPushButton, 'sendConfigBtn')
        self.send_config_button.clicked.connect(self.send_config)
        self.grab_config_button = self.findChild(QtGui.QPushButton, 'grabConfigBtn')
        self.grab_config_button.clicked.connect(self.grab_config)

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

        self.cam_props = self.setup_cam_prop_win()

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

    def grab_img(self):
        try:
            self.get_new_raw()
        except socket.error:
            QtGui.QMessageBox.warning(self, 'Connection error', 'No server running on defined IP')

    def send_config(self):
        class ConfigEncoder(json.JSONEncoder):
            def default(self, o):
                return o.__dict__
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.get_ip_addr(), 8621))  # TODO allow user-defined port (maybe)
            s.send('NEWCONFIG')  # We want to send a config
            s.recv(42)  # Enough to fit "READY"
            s.send(ConfigEncoder().encode(self.config))  # Send a json representation of our config
            response = s.recv(45)  # Enough to fit "SUCCESS" and "FAIL"
            s.close()
            if response == "SUCCESS":
                QtGui.QMessageBox.information(self, 'Config sent', 'Successfully sent config to server')
            else:
                QtGui.QMessageBox.warning(self, 'Error', 'Problem sending config')
        except socket.error:
            QtGui.QMessageBox.warning(self, 'Connection error', 'No server running on defined IP')

    def grab_config(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.get_ip_addr(), 8621))  # TODO allow user-defined port (maybe)
        s.send('GETCONFIG')  # We want to get a config
        newconf_data = s.recv(1024)
        s.close()
        newconf = json.loads(newconf_data)
        # Set config values
        self.config.min_val = newconf.get('min_val')
        self.config.max_val = newconf.get('max_val')
        self.config.min_sat = newconf.get('min_sat')
        self.config.max_sat = newconf.get('max_sat')
        self.config.min_hue = newconf.get('min_hue')
        self.config.max_hue = newconf.get('max_hue')
        # We changed config values manually, so let's update the sliders
        self.update_sliders()
        # Do processing with the new values we got
        self.process_image()

    def get_ip_addr(self):
        default_ip = '10.8.62.169'
        ip = str(self.ip_addr_box.text()).strip()
        if ' ' in ip or len(ip) is 0:  # If a space is in the input or the input is blank
            return default_ip
        return ip

    def update_sliders(self):
        """
        Update the sliders to the current config values
        """
        self.min_hue_slider.setValue(self.config.min_hue)
        self.max_hue_slider.setValue(self.config.max_hue)
        self.min_sat_slider.setValue(self.config.min_sat)
        self.max_sat_slider.setValue(self.config.max_sat)
        self.min_val_slider.setValue(self.config.min_val)
        self.max_val_slider.setValue(self.config.max_val)

    def setup_cam_prop_win(self):
        prop_win = QtGui.QDialog(self)
        grid = QtGui.QVBoxLayout()
        prop_win.setLayout(grid)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.get_ip_addr(), 8621))  # TODO allow user-defined port (maybe)
            s.send('GETCAMPROPS')  # We want to get a config
            length = int(s.recv(16))
            camprop_data = receive_all(s, length)
            s.close()
            int_prop_list = camprop.parse_int_props(camprop_data)
            cam_prop_num = 0
            sheight = 0
            for prop in int_prop_list:
                slider = QtGui.QSlider(orientation=QtCore.Qt.Horizontal)
                def update_value(value):
                    for p in int_prop_list:
                        if p.name == self.sender().objectName():
                            p.new_value = value
                prop_win.connect(slider, QtCore.SIGNAL("valueChanged(int)"), update_value)
                slider.setMinimum(prop.min)
                slider.setMaximum(prop.max)
                slider.setSingleStep(prop.step)
                slider.setValue(prop.value)
                slider.setToolTip(prop.name)
                slider.setObjectName(prop.name)
                y = cam_prop_num*(slider.height()-10)
                slider.move(0, y)
                cam_prop_num += 1
                label = QtGui.QLabel()
                label.setText(prop.name)
                label.move(slider.width(), y)
                sheight = slider.height()
                grid.addWidget(label)
                grid.addWidget(slider)
                y = cam_prop_num*(sheight-10)
                btn = QtGui.QPushButton(parent=prop_win)
                btn.setText('Send')
                btn.clicked.connect(self.send_changed_props)
                btn.move(0, y)
                grid.addWidget(btn)
        except socket.error:
            int_prop_list = []

        prop_win.setWindowTitle('Camera Properties')
        prop_win.show()

        return int_prop_list

    def send_changed_props(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.get_ip_addr(), 8621))  # TODO allow user-defined port (maybe)
        s.send("STARTV4LPROPS")
        time.sleep(1)  # Sleep for 1 second so that it gets out start message
        for prop in self.cam_props:
            if prop.value != prop.new_value:
                upstr = 'UPDATEV4L %s %s' % (prop.name, prop.new_value)
                s.send(str(len(upstr)).ljust(16))  # Send the length, we do this so we can discriminate between multiple values sent in quick intervals
                s.send(upstr)  # Send the command
                prop.value = prop.new_value  # Set the value to the new value so that we don't send the same change again
        s.send(str(len("ENDV4LPROPS")).ljust(16))
        s.send("ENDV4LPROPS")
        s.close()
