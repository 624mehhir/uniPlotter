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

FONT = cv2.FONT_HERSHEY_SIMPLEX


def _color_for_label(label):
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(PALETTE)
    return PALETTE[index]


def _text_color_for(bg_color):
    b, g, r = bg_color
    luminance = 0.114 * b + 0.587 * g + 0.299 * r
    return (255, 255, 255) if luminance < 140 else (20, 20, 20)


def _shape_bbox(points, shape_type):
    if shape_type == "bbox":
        x_min, y_min, width, height = points
        return x_min, y_min, x_min + width, y_min + height
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _rects_overlap(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def draw_annotations(image, annotations):
    output = image.copy()
    overlay = output.copy()
    img_h, img_w = output.shape[:2]

    dim = max(img_h, img_w)
    thickness = max(1, round(dim / 500))
    # Label text scale is capped independently of shape thickness/dim so it
    # stays legible instead of ballooning on large real-world images.
    font_scale = max(0.35, min(0.6, dim / 3000))
    text_thickness = 1

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

    # Labels are placed in a second pass, ordered top-to-bottom, so each new
    # label can be pushed clear of every label already placed above it —
    # this is what prevents nearby annotations' labels from stacking on top
    # of each other on densely-annotated images.
    order = sorted(
        range(len(annotations)),
        key=lambda i: _shape_bbox(annotations[i]["points"], annotations[i]["shape_type"])[1],
    )
    placed = []
    pad_x, pad_y = 4, 3

    for i in order:
        ann = annotations[i]
        color = colors[i]
        label = ann["label"]
        x1, y1, x2, y2 = _shape_bbox(ann["points"], ann["shape_type"])

        (text_w, text_h), baseline = cv2.getTextSize(label, FONT, font_scale, text_thickness)
        box_w = text_w + 2 * pad_x
        box_h = text_h + baseline + 2 * pad_y

        # Prefer sitting just above the shape's own bounding box so the
        # label never covers the shape it names.
        box_x = int(x1)
        box_y = int(y1) - box_h - 2
        if box_y < 0:
            box_y = int(y2) + 2
            if box_y + box_h > img_h:
                box_y = 0

        box_x = max(0, min(box_x, img_w - box_w))
        rect = [box_x, box_y, box_x + box_w, box_y + box_h]

        attempts = 0
        while any(_rects_overlap(rect, other) for other in placed) and attempts < 100:
            rect[1] += box_h + 2
            rect[3] += box_h + 2
            attempts += 1

        placed.append(tuple(rect))

        cv2.rectangle(output, (rect[0], rect[1]), (rect[2], rect[3]), color, -1)
        text_color = _text_color_for(color)
        text_origin = (rect[0] + pad_x, rect[3] - pad_y - baseline)
        cv2.putText(
            output,
            label,
            text_origin,
            FONT,
            font_scale,
            text_color,
            text_thickness,
            cv2.LINE_AA,
        )

    return output
