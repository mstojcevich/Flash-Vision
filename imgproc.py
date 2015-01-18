from SimpleCV import *
import numpy


def process_image(obj, img, config):
    """
    :param obj: Object we're tracking
    :param img: Input image
    :param config: Controls
    :return: Mask with candidates surrounded in a green rectangle
    """
    hsv_image = img.toHSV()
    segmented = Image(cv2.inRange(hsv_image.getNumpy(),
                                  # TODO I just changed this from getNumpyCv2 to getNumpy which rotated it 90 degrees. See if the blob drawing is fine.
                                  numpy.array([config.min_hue, config.min_sat, config.min_val]),
                                  numpy.array([config.max_hue, config.max_sat, config.max_val])))

    segmented = segmented.dilate(2)
    blobs = segmented.findBlobs()
    if blobs:
        for b in blobs:
            if b.radius() > 10:
                rect_width = b.minRectWidth()
                rect_height = b.minRectHeight()
                # Yes, I know this is backwards. No, I don't know why, but it works.
                # TODO this might actually be wrong now that I changed it from numpycv2
                aspect_ratio = rect_height / rect_width
                square_error = abs(obj.aspect_ratio - aspect_ratio) / abs(aspect_ratio)
                if square_error < 0.1:
                    segmented.drawRectangle(b.minRectX() - rect_width / 2, b.minRectY() + rect_height / 2, rect_width,
                                            -rect_height, color=Color.GREEN, width=3)

    # Give the result mask
    return segmented