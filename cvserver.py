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

cam_id = 0

x_offset = -1
y_offset = -1


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
        not_found_count = 0
        max_not_found = 3

        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)  # Timeout @ 2 secs
            s.connect(('169.254.65.94', 8622))
        except socket.error:
            s = None


        lastConnectRetry = 0
        while True:
            input_img = self.camera.getImage()
            found = False

            def on_blob(b):
                global found
                global not_found_count
                global s
                global lastConnectRetry

                rect_width = b.minRectWidth()
                rect_height = b.minRectHeight()

                rect_ctr_x = b.minRectX()

                mrX = rect_ctr_x-rect_width/2
                mrY = b.minRectY()-rect_height/2
                # px * (px/cm) = cm
                x_offset = int(round((rect_ctr_x - input_img.width/2) * (obj.width / rect_width)))
                found = True
                not_found_count = 0

                print("Sending a real value!")
                if s is not None:
                    try:
                        to_send = "x=-1;y=%d;" % x_offset  # x is not yet implemented
                        s.send(str(len(to_send)).ljust(16))
                        s.send(to_send)
                        s.close()
                    except socket.error:
                        s = None  # So we will try to reconnect later
                elif int(round(time.time() * 1000)) - lastConnectRetry > 30000:  # If we haven't retried for 30 seconds
                    print("Trying to reconnect to the rio.")
                    lastConnectRetry = int(round(time.time() * 1000))
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(2)  # Timeout @ 2 secs
                        s.connect(('169.254.65.94', 8622))
                    except socket.error:
                        s = None

            if not found:
                not_found_count += 1
            if not_found_count >= max_not_found:
                # It's been missing for a bit now, let's send some arbitrary negative numbers!
                to_send = "x=-10;y=-10"
                print("SENDING -10!")
                if s is not None:
                    try:
                        s.send(str(len(to_send)).ljust(16))
                        s.send(to_send)
                        s.close()
                    except socket.error:
                        pass

            processed_img = imgproc.process_image(self.obj, input_img, self.config, on_blob)
            time.sleep(0.5)


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
obj = Obj(38.1, 30.48)  # Values are measured from the yellow tote, TODO load from config file


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
