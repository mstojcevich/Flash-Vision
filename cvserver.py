import socket

from SimpleCV import Camera, Image
import cv2
import numpy
import sys
import os
import time
import imgproc
import json
from config import Config
from object import Obj
from threading import Thread
import threading


# Really hacky way to detect if the camera is connected. Always returns true on Windows and OSX.
# TODO maybe this doesn't have to return true always on OSX, but I doubt we'll ever have an OSX machine running this.
def camera_connected():
    if sys.platform == 'linux' or sys.platform == 'linux2':
        # TODO, look for any /dev/video since the camera doesn't have to be video0
        return os.path.exists('/dev/video0')  # The system sees a camera
    else:
        return True


# Does image processing
class ImgProcThread(Thread):
    def __init__(self, camera, obj, config):
        super(ImgProcThread, self).__init__()
        self.camera = camera
        self.obj = obj
        self.config = config

    def run(self):
        def on_blob(b):
            print("Found blob centered at (%s,%s)" % (int(b.minRectX()), int(b.minRectY())))
        while True:
            input_img = self.camera.getImage()
            processed_img = imgproc.process_image(self.obj, input_img, self.config, on_blob)


class ServerThread(Thread):
    def __init__(self, camera):
        super(ServerThread, self).__init__()
        self.camera = camera

    def run(self):
        port = 8621
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('localhost', port))
        server_socket.listen(1)  # max 1 connection - we only have one camera, so we can't send images to two people at once
        print('Listening on port %s' % port)
        while True:
            connection, address = server_socket.accept()
            data = connection.recv(1024)
            print('Got some data:')
            print(data)
            print("Data over.")
            if data == 'GETIMG':  # They want a raw image
                try:
                    if camera_connected():
                        # give them the current camera image
                        img = c.getImage()
                    else:  # Looks like the camera disconnected randomly
                        img = Image("res/img/connect_failed.png")
                except AttributeError:  # Occurs when the camera was never connected in the first place
                    img = Image("res/img/connect_failed.png")

                # Encode as JPEG so we don't have to send so much
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                result, encoded_img = cv2.imencode('.jpg', img.getNumpy(), encode_param)

                img_numpy = numpy.array(encoded_img)
                img_str = img_numpy.tostring()

                # Send the size of the image, so that the client can handle if we have to send it in multiple parts
                connection.send(str(len(img_str)).ljust(16))
                # Send the image itself
                connection.send(img_str)
            elif data == "NEWCONFIG":  # They're sending us a new config to use
                connection.send('READY')
                newconf_data = connection.recv(1024)
                newconf = json.loads(newconf_data)

                # Set values to the new ones we just got
                conf.min_val = newconf.get('min_val')
                conf.max_val = newconf.get('max_val')
                conf.min_sat = newconf.get('min_sat')
                conf.max_sat = newconf.get('max_sat')
                conf.min_hue = newconf.get('min_hue')
                conf.max_hue = newconf.get('max_hue')
                # TODO save changes to file
                connection.send('SUCCESS')  # We successfully processed the new config
                print('Got a new config')

c = Camera()
conf = Config()  # TODO load config from file
obj = Obj(38.1, 30.48)  # Values are measured from the yellow tote, TODO load from config file

# Create and spawn the processing thread
procThread = ImgProcThread(c, obj, conf)
procThread.daemon = True
procThread.start()

# Create and spawn the server thread
srvThread = ServerThread(c)
srvThread.daemon = True
srvThread.start()

# Wait for both threads to be done before we shutdown
while threading.active_count > 0:
    time.sleep(0.1)  # Keeps us responsive
