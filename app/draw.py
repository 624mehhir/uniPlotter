import hashlib

import cv2
import numpy as np

PALETTE = [
    (255, 99, 71),    # tomato
    (60, 179, 113),   # medium sea green
    (65, 105, 225),   # royal blue
    (238, 130, 238),  # violet
    (255, 215, 0),    # gold
    (0, 191, 255),    # deep sky blue
    (255, 140, 0),    # dark orange
    (147, 112, 219),  # medium purple
    (0, 206, 209),    # dark turquoise
    (220, 20, 60),    # crimson
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
    for ann in annotations:
        color = _color_for_label(ann["label"])
        shape_type = ann["shape_type"]
        points = ann["points"]

        if shape_type == "polygon":
            pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
            overlay = image.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.25, image, 0.75, 0, image)
            cv2.polylines(image, [pts], isClosed=True, color=color, thickness=2)
        elif shape_type == "bbox":
            x_min, y_min, width, height = points
            pt1 = (int(x_min), int(y_min))
            pt2 = (int(x_min + width), int(y_min + height))
            cv2.rectangle(image, pt1, pt2, color, 2)
        else:
            raise ValueError(f"Unknown shape_type: {shape_type!r}")

        label_pos = _label_position(points, shape_type)
        cv2.putText(
            image,
            ann["label"],
            label_pos,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
            cv2.LINE_AA,
        )

    return image
