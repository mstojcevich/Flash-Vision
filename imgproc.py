from SimpleCV import *
import numpy
import cv2


def process_image(obj, img, config, each_blob=None):
    """
    :param obj: Object we're tracking
    :param img: Input image
    :param config: Controls
    :param each_blob: function, taking a SimpleCV.Blob as an argument, that is called for every candidate blob
    :return: Mask with candidates
    """
    hsv_image = img.toHSV()
    segmented = Image(cv2.inRange(hsv_image.rotate90().getNumpyCv2(),
                                  numpy.array([config.min_hue, config.min_sat, config.min_val]),
                                  numpy.array([config.max_hue, config.max_sat, config.max_val])))

    segmented = segmented.dilate(2)
    blobs = segmented.findBlobs()
    if blobs:
        for b in blobs:
            if b.radius() > 10:
                rect_width = b.minRectWidth()
                rect_height = b.minRectHeight()
                aspect_ratio = rect_width / rect_height
                square_error = abs(obj.aspect_ratio - aspect_ratio) / abs(aspect_ratio)
                if square_error < 0.1:
                    if not each_blob:  # default to just outlining
                        # minRectX and minRectY actually give the center point, not the minX and minY, so we shift by 1/2
                        rect_ctr_x = b.minRectX()
                        mrX = rect_ctr_x-rect_width/2
                        mrY = b.minRectY()-rect_height/2
                        segmented.drawRectangle(mrX, mrY, rect_width,
                                                rect_height, color=Color.GREEN, width=6)
                        # px * (px/cm) = cm
                        offset = int(round((rect_ctr_x - segmented.width/2) * (obj.width / rect_width)))
                        segmented.drawText('Offset %s cm' % offset, mrX, mrY, Color.RED, 64)
                    else:
                        each_blob(b)

    # Give the result mask
    return segmented.applyLayers()