import numpy as np
import cv2
from .transforms import img2euc, euc2img, shift


def make_rgb_view(arr, detections, win_size, bb_color=(0, 255, 0)):

    if detections is None:
        return arr

    scale = max(1, win_size[0] // 700)

    arr = cv2.resize(arr, win_size)

    h, w = arr.shape[:2]
    scores = detections[:, 2]

    # loop over the detections
    for (_, _, score, x1, y1, x2, y2) in detections[
        scores > 0.2
    ]:  # TODO: put the thresholding outside

        # scale box
        box = np.array([x1, y1, x2, y2]) * np.array([w, h, w, h])

        # cast to int
        (x1, y1, x2, y2) = box.astype("int")

        # draw box
        cv2.rectangle(arr, (x1, y1), (x2, y2), bb_color, 2*scale)

        # put text
        cv2.putText(
            arr,
            f"face: {round(score*100,0):2.0f}%",
            (x1, y1 - 10 if y1 > 20 else y1 + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45 * scale,
            bb_color,
            2,
        )

    # draw rectangle to show the approx. IR overlay on VIS frame
    # draw_rectangle(arr)

    return arr


def normalize_ir(ir_arr):
    ir_arr_normalized = cv2.normalize(
        ir_arr, None, 0, 255, cv2.NORM_MINMAX
    )  # normalize to 0-255
    ir_arr_normalized = ir_arr_normalized.astype(np.uint8)  # convert to uint8
    return ir_arr_normalized


def apply_cmap(ir_arr, threshold=36):

    ir_arr_n = normalize_ir(ir_arr)
    ir_arr_n = ir_arr_n.astype(np.uint8)
    arr_3ch = cv2.cvtColor(ir_arr_n, cv2.COLOR_GRAY2BGR)

    ir_arr_n = cv2.applyColorMap(ir_arr_n, cv2.COLORMAP_JET)

    mask = ir_arr < threshold
    mask = np.stack(3 * [mask], axis=-1)

    return np.where(mask, arr_3ch, ir_arr_n)


def ctof(c):
    f = (c * 9 / 5) + 32
    return f

def draw_rectangle(arr):
    center = np.array([0.5, 0.5])
    wh = np.array([0.5, 0.5])

    p1 = np.array([center[0] - wh[0] / 2, center[1] - wh[1] / 2])

    p2 = np.array([center[0] + wh[0] / 2, center[1] + wh[1] / 2])

    # scale it to image size
    s = np.array(arr.shape[:2][::-1])

    p1 = tuple(np.array(p1 * s, dtype=np.int))
    p2 = tuple(np.array(p2 * s, dtype=np.int))

    cv2.rectangle(arr, p1, p2, (255, 255, 255), 1)

def make_gyr_cmap(temps_arr, thr=[30, 36, 36]):
    """
    make heatmap colorized with blue, yellow and red according to following thresholds
    """
    hmap = np.zeros((*temps_arr.shape[:2], 3), dtype=np.uint8)

    green_mask = np.logical_and(temps_arr > thr[0], temps_arr < thr[1])
    yellow_mask = np.logical_and(temps_arr > thr[1], temps_arr < thr[2])
    red_mask = temps_arr > thr[2]

    hmap[green_mask] = (0, 255, 0)  # green
    hmap[yellow_mask] = (0, 255, 255)  # yellow
    hmap[red_mask] = (0, 0, 255)  # red

    return hmap


def make_bin_cmap(temps_arr, thr=37):
    """
    colorize with red above thr
    """
    hmap = np.zeros((*temps_arr.shape[:2], 3), dtype=np.uint8)
    hmap[temps_arr > thr] = (0, 0, 255)  # red

    return hmap


def make_ir_view(rgb_arr, ir_arr, detections, temps_arr, win_size, bb_color=(255,0,0)):

    # scaling width, scaling height
    SW, SH = 0.9, 0.9

    ir_arr = cv2.resize(ir_arr, win_size)
    temps_arr = cv2.resize(temps_arr, win_size)

    # 1ch -> 3ch
    ir_arr = cv2.cvtColor(ir_arr, cv2.COLOR_GRAY2BGR)

    # hmap = make_gyr_cmap(temps_arr)
    hmap = make_bin_cmap(temps_arr, thr=36)
    ir_arr = cv2.addWeighted(ir_arr, 0.5, hmap, 0.5, 0)

    if detections is None:
        return ir_arr

    h_rgb, w_rgb = rgb_arr.shape[:2]
    h_ir, w_ir = ir_arr.shape[:2]

    scores = detections[:, 2]

    # loop over the detections
    for (_, _, score, x1, y1, x2, y2) in detections[
        scores > 0.2
    ]:  # TODO: adjustable threshold

        # TODO: interface should only receive the detections after transform!
        # box in euclidean rgb frame
        x1, y1 = img2euc(x1, y1)
        x2, y2 = img2euc(x2, y2)

        # scale to convert to ir frame
        x1 /= SW
        x2 /= SW
        y1 /= SH
        y2 /= SH

        # shift left
        x1, y1 = shift(x1, y1, 0, 0.03)
        x2, y2 = shift(x2, y2, 0, 0.03)

        # convert back to image frame
        x1, y1 = euc2img(x1, y1)
        x2, y2 = euc2img(x2, y2)

        # scale
        box = np.array([x1, y1, x2, y2])
        box *= np.array([w_ir, h_ir, w_ir, h_ir])

        # cast to int
        (x1, y1, x2, y2) = box.astype("int")

        # draw box
        cv2.rectangle(ir_arr, (x1, y1), (x2, y2), bb_color, 2)

        roi = temps_arr[y1:y2, x1:x2]
        temp = np.nanmean(roi[roi > 32])

        # put text
        cv2.putText(
            ir_arr,
            f"{temp:.2f} C {ctof(temp):.2f} F",
            (x1, y1 - 10 if y1 > 20 else y1 + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            bb_color,
            2,
        )

    return ir_arr
