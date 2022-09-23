import numpy as np


def relabel_points(data, body_parts, scale_factor):
    """
    Relabel badly tracked body points again
    :param data: the new tracked points from the relabeling
    :param body_parts: the body parts from the config file
    :param scale_factor: the fraction used to resize the frames
    :return: new tracked points adjusted to the actual dimensions for the video
    """

    animals_bodyparts = {}
    for an in data.keys():
        body_pts = {}
        for bp in body_parts:
            if bp in data[an].keys():
                body_pts[bp] = np.array(data[an][bp])
            else:
                body_pts[bp] = np.array([np.nan, np.nan])
        animals_bodyparts[an] = body_pts

    animals_bpts = {}
    for an in data.keys():
        body_pts = animals_bodyparts[an].values()
        pts = []
        for bpt in body_pts:
            for i, v in enumerate(bpt):
                # new x and y coordinate
                new_v = v * (1 / scale_factor)
                pts.append(new_v)
        animals_bpts[an] = np.array(pts)

    return animals_bpts
