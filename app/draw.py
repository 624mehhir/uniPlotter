import hashlib

import cv2
import numpy as np

# BGR order (cv2 native), not RGB.
PALETTE = [
    (71, 99, 255),    # tomato
    (113, 179, 60),   # medium sea green
    (225, 105, 65),   # royal blue
    (238, 130, 238),  # violet
    (0, 215, 255),    # gold
    (255, 191, 0),    # deep sky blue
    (0, 140, 255),    # dark orange
    (219, 112, 147),  # medium purple
    (209, 206, 0),    # dark turquoise
    (60, 20, 220),    # crimson
]


def _color_for_label(label):
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(PALETTE)
    return PALETTE[index]


def _label_position(points, shape_type):
    if shape_type == "polygon":
        x, y = points[0]
    else:
        x, y = points[0], points[1]
    x, y = int(x), int(y)
    return (x, y - 8) if y - 8 > 0 else (x, y + 16)


def draw_annotations(image, annotations):
    output = image.copy()
    overlay = output.copy()

    dim = max(output.shape[:2])
    thickness = max(1, round(dim / 500))
    font_scale = max(0.4, dim / 1600)

    colors = [_color_for_label(ann["label"]) for ann in annotations]

    has_fill = False
    for ann, color in zip(annotations, colors):
        if ann["shape_type"] == "polygon":
            pts = np.array(ann["points"], dtype=np.int32).reshape((-1, 1, 2))
            cv2.fillPoly(overlay, [pts], color)
            has_fill = True

    if has_fill:
        cv2.addWeighted(overlay, 0.25, output, 0.75, 0, output)

    for ann, color in zip(annotations, colors):
        shape_type = ann["shape_type"]
        points = ann["points"]

        if shape_type == "polygon":
            pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(output, [pts], isClosed=True, color=color, thickness=thickness)
        elif shape_type == "bbox":
            x_min, y_min, width, height = points
            pt1 = (int(x_min), int(y_min))
            pt2 = (int(x_min + width), int(y_min + height))
            cv2.rectangle(output, pt1, pt2, color, thickness)
        else:
            raise ValueError(f"Unknown shape_type: {shape_type!r}")

        label_pos = _label_position(points, shape_type)
        cv2.putText(
            output,
            ann["label"],
            label_pos,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA,
        )

    return output
