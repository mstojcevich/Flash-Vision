from SimpleCV import *
import time
import numpy

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


def matchKeyPoints(image, template, quality=100):
    mode = "SURF"
    if not hasattr(cv2, "FeatureDetector_create"):
        warnings.warn("OpenCV >= 2.4.3 required")
        return None
    if template == None:
        return None
    detector = cv2.FeatureDetector_create(mode)
    descriptor = cv2.DescriptorExtractor_create(mode)
    img = image.getNumpyCv2()
    template_img = template.getNumpyCv2()

    skp = detector.detect(img)
    skp, sd = descriptor.compute(img, skp)

    tkp = detector.detect(template_img)
    tkp, td = descriptor.compute(template_img, tkp)

    idx, dist = image._getFLANNMatches(sd, td)
    dist = dist[:,0]/2500.0
    dist = dist.reshape(-1,).tolist()
    idx = idx.reshape(-1).tolist()
    indices = range(len(dist))
    indices.sort(key=lambda i: dist[i])
    dist = [dist[i] for i in indices]
    idx = [idx[i] for i in indices]
    sfs = []
    for i, dis in itertools.izip(idx, dist):
        if dis < quality:
            sfs.append(KeyPoint(template, skp[i], sd, mode))
        else:
            break #since sorted

    return sfs


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
img = img.toGray()
img = img.resize(640, 480)
firstlogo = firstlogo.toGray()

start_time = int(round(time.time() * 1000))
kpts = matchKeyPoints(img, firstlogo, 100)
end_time = int(round(time.time() * 1000))
print("Took %d ms" % (end_time-start_time))

xPts = []
yPts = []
if kpts:
    for kp in kpts:
        xPts.append(kp.x)
        yPts.append(kp.y)
avgX = int(numpy.average(xPts))
avgY = int(numpy.average(yPts))
print(avgX)
print(avgY)
img.drawCircle((avgY, avgX), 10, (255, 0, 0), 5)

img.applyLayers()

while disp.isNotDone():
    img.save(disp)