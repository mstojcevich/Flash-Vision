from SimpleCV import *
import cv2
import numpy


disp = Display((640, 480))

min_hue = 0
min_val = 64
min_sat = 0
max_hue = 360
max_val = 128
max_sat = 10

target_aspect_ratio = 1.245

img = Image("res/img/greytest2.jpg")
firstlogo = Image("res/img/firstlogo_grey.jpg")

while disp.isNotDone():
    keypoints = img.findKeypointMatch(firstlogo)
    if keypoints:
        keypoints.draw()
        img.applyLayers()
    img.save(disp)