from SimpleCV import *
import time
import numpy
import itertools


def filter_matches(kp1, kp2, matches, ratio=0.75):
    mkp1, mkp2 = [], []
    for m in matches:
        if len(m) == 2 and m[0].distance < m[1].distance * ratio:
            m = m[0]
            mkp1.append(kp1[m.queryIdx])
            mkp2.append(kp2[m.trainIdx])
    p1 = np.float32([kp.pt for kp in mkp1])
    p2 = np.float32([kp.pt for kp in mkp2])
    kp_pairs = zip(mkp1, mkp2)
    return p1, p2, kp_pairs


def getFLANNMatches(sd, td, mode):
    try:
        import cv2
    except:
        logger.warning("Can't run FLANN Matches without OpenCV >= 2.3.0")
        return
    FLANN_INDEX_KDTREE = 1  # bug: flann enums are missing
    if mode == 'ORB':
        flann_params = dict(algorithm=6,
                            table_number=6,
                            key_size=12,
                            multi_probe_level=1)
    else:
        flann_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=4)
    flann = cv2.flann_Index(sd, flann_params)
    idx, dist = flann.knnSearch(td, 1, params={})  # bug: need to provide empty dict
    del flann
    return idx, dist


def matchKeyPoints(image, template, quality=0.00005):
    mode = "SURF"
    if not hasattr(cv2, "FeatureDetector_create"):
        warnings.warn("OpenCV >= 2.4.3 required")
        return None
    if template == None:
        return None
    detector = cv2.SURF(750, upright=1)  # First number bigger = more picky
    img = image.getNumpyCv2()
    template_img = template.getNumpyCv2()

    start_time = int(round(time.time() * 1000))
    skp, sd = detector.detectAndCompute(img, None)
    end_time = int(round(time.time() * 1000))
    print("Image detect and compute took %s ms" % (end_time-start_time))

    tkp, td = detector.detectAndCompute(template_img, None)

    if skp is None or tkp is None or sd is None or td is None:
        return None
    idx, dist = getFLANNMatches(sd, td, mode)
    dist = dist[:, 0] / 2500.0
    dist = dist.reshape(-1, ).tolist()
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
            break  # since sorted

    return sfs


def main():
    disp = Display((640, 480))

    firstlogo = Image("res/img/firstlogo_grey.jpg")
    firstlogo = firstlogo.toGray()

    c = Camera(0, prop_set={"width": 640, "height": 480})

    while disp.isNotDone():
        cImg = c.getImage()
        cImg = cImg.toGray()
        third = cImg.height/3
        cImg = cImg.crop(0, third, cImg.width, third)
        start_time = int(round(time.time() * 1000))
        kpts = matchKeyPoints(cImg, firstlogo)
        end_time = int(round(time.time() * 1000))
        print("Total feature detect took %d ms" % (end_time - start_time))

        if kpts is not None:
            if len(kpts) > 0:
                xPts = []
                yPts = []
                if kpts:
                    for kp in kpts:
                        xPts.append(kp.x)
                        yPts.append(kp.y)
                avgX = int(numpy.average(xPts))
                avgY = int(numpy.average(yPts))
                cImg.drawCircle((avgY, avgX), 10, (255, 0, 0), 5)

            cImg.mergedLayers()

        cImg.save(disp)


main()