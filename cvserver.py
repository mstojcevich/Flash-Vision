import socket

from SimpleCV import Camera, Image
import cv2
import numpy
import sys
import os
import time
import imgproc
import json
from valueconfig import ValueConfig
from object import Obj
from threading import Thread
import threading
import subprocess


wait_for_rio = 0
look_for_tote = 1

WAIT_BETWEEN_SEND_TIME = 0.5 # Change to 0 for production

ROBORIO_IP = '10.8.62.2'
ROBORIO_LISTEN_PORT = 8622

CONFIG_LISTEN_HOST = ''
CONFIG_LISTEN_PORT = 8621

FOCAL_LENGTH = 636.0

cam_id = 0

x_offset = -1
y_offset = -1

global mode
mode = wait_for_rio

NO_RIO = True


# Really hacky way to detect if the camera is connected. Always returns true on Windows and OSX.
# TODO maybe this doesn't have to return true always on OSX, but I doubt we'll ever have an OSX machine running this.
def camera_connected():
    if sys.platform == 'linux' or sys.platform == 'linux2':
        # TODO, look for any /dev/video since the camera doesn't have to be video0
        return os.path.exists('/dev/video%s' % cam_id)  # The system sees a camera
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
        global found
        global not_found_count
        global s
        global lastConnectRetry
        global mode
        not_found_count = 0
        max_not_found = 3

        if NO_RIO:
            s = None
            mode = look_for_tote
        else:
            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)  # Timeout @ 0.5 secs
                s.connect((ROBORIO_IP, ROBORIO_LISTEN_PORT))
                mode = look_for_tote
            except socket.error as err:
                mode = wait_for_rio
                print("Failed to connect to RoboRio: %s" % err)
                s = None

        lastConnectRetry = 0
        while True:
            if mode is wait_for_rio and not NO_RIO:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)  # Timeout @ 0.5 secs
                    s.connect((ROBORIO_IP, ROBORIO_LISTEN_PORT))
                    mode = look_for_tote
                except socket.error as err:
                    print("Failed to connect to RoboRio: %s" % err)
                    s = None
                    time.sleep(0.2)
            elif mode is look_for_tote:
                input_img = self.camera.getImage()
                found = False

                def on_blob(b):
                    global found
                    global not_found_count
                    global s
                    global lastConnectRetry
                    global mode

                    rect_width = b.minRectWidth()
                    rect_height = b.minRectHeight()
                    max_side = max(rect_width, rect_height)
                    min_side = min(rect_width, rect_height)
                    rect_width = max_side
                    rect_height = min_side

                    rect_ctr_x = b.minRectX()
                    rect_ctr_y = b.minRectY()

                    mrX = rect_ctr_x-rect_width/2
                    mrY = b.minRectY()-rect_height/2
                    # px * (px/cm) = cm
                    print("img width,height %d,%d" % (input_img.width, input_img.height))
                    x_offset = int(round((rect_ctr_x - input_img.width/2) * (obj.width / rect_width)))
                    # TODO the server things x is y and y is x and wtf
                    y_offset = int(obj.width*FOCAL_LENGTH/rect_width)
                    found = True
                    not_found_count = 0

                    print("Trying to send a real value")
                    if s is not None or NO_RIO:
                        print("We're really sending it")
                        try:
                            to_send = "x=%d;y=%d;" % (-y_offset, x_offset)  # x is not yet implemented
                            print(to_send)
                            if not NO_RIO:
                                s.send(str(len(to_send)).ljust(16))
                                s.send(to_send)
                        except socket.error as err:
                            print("Failed to connect to RoboRio: %s" % err)
                            mode = wait_for_rio
                            s = None  # The socket's bad now

                if not found:
                    not_found_count += 1
                if not_found_count >= max_not_found:
                    # It's been missing for a bit now, let's send some arbitrary negative numbers!
                    to_send = "x=-10;y=-10"
                    print("SENDING -10! WE DIDN'T SEE ANYTHING")
                    if s is not None:
                        try:
                            s.send(str(len(to_send)).ljust(16))
                            s.send(to_send)
                        except socket.error as err:
                            print("Failed to connect to RoboRio: %s" % err)
                            mode = wait_for_rio
                            s = None

                processed_img = imgproc.process_image(self.obj, input_img, self.config, on_blob, False)
                time.sleep(WAIT_BETWEEN_SEND_TIME)


class ServerThread(Thread):
    def __init__(self, camera):
        super(ServerThread, self).__init__()
        self.camera = camera

    def run(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((CONFIG_LISTEN_HOST, CONFIG_LISTEN_PORT))
        server_socket.listen(1)  # max 1 connection - we only have one camera, so we can't send images to two people at once
        print('Listening on port %s' % CONFIG_LISTEN_PORT)
        connection = None
        while True:
            connection, address = server_socket.accept()
            try:  # Don't let any bad things that happen with one connection cause the whole server to crash
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
                    result, encoded_img = cv2.imencode('.jpg', img.getNumpyCv2(), encode_param)

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
                    connection.send('SUCCESS')  # We successfully processed the new config
                    print('Got a new config')
                    conf.save("conf/values.json")  # Save our new config
                elif data == "GETCONFIG":
                    class ConfigEncoder(json.JSONEncoder):
                        def default(self, o):
                            return o.__dict__
                    connection.send(ConfigEncoder().encode(conf))  # Send a json representation of our config
                elif data == "GETCAMPROPS":
                    proc = subprocess.Popen(['v4l2-ctl', '--list-ctrls', '--device=/dev/video%s' % cam_id],
                                            stdout=subprocess.PIPE)
                    out, err = proc.communicate()
                    connection.send(str(len(out)).ljust(16))
                    connection.send(out)
                elif data == "STARTV4LPROPS":
                    while True:
                        length = int(connection.recv(16))
                        dta = connection.recv(length)
                        if dta is None or dta == "ENDV4LPROPS" or not dta.startswith('UPDATEV4L'):
                            break
                        else:
                            words = dta.split(' ')
                            val_name = words[1].strip()
                            val_value = int(words[2].strip())
                            print(val_name)
                            print(val_value)
                            proc = subprocess.Popen(['v4l2-ctl', "--device=/dev/video%s" % cam_id, '-c',
                                                     "%s=%s" % (val_name, val_value)],
                                                    stdout=subprocess.PIPE)
                            # TODO see if the command is good
                            proc.communicate()

            except Exception as ex:
                print(ex.message)
                connection.close()
        connection.close()

c = Camera(camera_index=cam_id)
conf = ValueConfig("conf/values.json")
try:
    obj = Obj("conf/object.json")
except Exception:
    obj = None


# TODO this is very likely camera specific!!!
# Disable auto exposure on the rocketfish camera
proc = subprocess.Popen(['v4l2-ctl', '-d', '/dev/video%s' % cam_id, '-c', 'exposure_auto=1'],
                        stdout=subprocess.PIPE)
out, err = proc.communicate()

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
