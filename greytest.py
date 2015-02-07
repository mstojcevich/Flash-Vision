from SimpleCV import *
import time


def filter_matches(kp1, kp2, matches, ratio = 0.75):
    mkp1, mkp2 = [], []
    for m in matches:
        if len(m) == 2 and m[0].distance < m[1].distance * ratio:
            m = m[0]
            mkp1.append( kp1[m.queryIdx])
            mkp2.append( kp2[m.trainIdx])
    p1 = np.float32([kp.pt for kp in mkp1])
    p2 = np.float32([kp.pt for kp in mkp2])
    kp_pairs = zip(mkp1, mkp2)
    return p1, p2, kp_pairs


disp = Display((640, 480))

min_hue = 0
min_val = 64
min_sat = 0
max_hue = 360
max_val = 128
max_sat = 10

target_aspect_ratio = 1.245

img = Image("res/img/greytest.jpg")
firstlogo = Image("res/img/firstlogo_grey.jpg")

# Would it help to convert things to B&W?

start_time = int(round(time.time() * 1000))
keypoints = img.findKeypointMatch(firstlogo, 100.00, 0.3, 0.1)
end_time = int(round(time.time() * 1000))
print("Took %d ms" % (end_time-start_time))

if keypoints:
    keypoints[0].draw(width=4)
    print("%s->%s, %s->%s" % (keypoints.x(), keypoints.x()+keypoints.width(),
                              keypoints.y(), keypoints.y()+keypoints.height()))

img.applyLayers()

while disp.isNotDone():
    img.save(disp)