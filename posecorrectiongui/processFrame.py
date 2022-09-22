import cv2


def process_frame(image, scale_factor=0.5):
    """
    Resizes the image before it is plotted in the GUI
    :param image: the image
    :param scale_factor: the fraction to resize the image by - ranges from 0 to 1. 0.5 is recommended
    :return:
    """
    height, width = image.shape[:2]
    height = int(height * scale_factor)
    width = int(width * scale_factor)
    dim = (width, height)
    image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
    return image
