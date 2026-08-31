import hashlib
import math

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
    (109, 242, 176),  # light yellow-green
    (242, 242, 109),  # cyan
    (166, 65, 217),   # magenta
    (109, 176, 242),  # light orange
    (153, 242, 109),  # mint green
    (65, 217, 116),   # green
    (217, 191, 65),   # sky blue
    (109, 242, 242),  # pale yellow
]

FONT = cv2.FONT_HERSHEY_SIMPLEX


def _palette_index_for_label(label):
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()
    return int(digest, 16) % len(PALETTE)


def _assign_label_colors(labels_in_order):
    """Hash-based color per distinct label, with same-image collisions
    reassigned by linear-probing forward to the next unused palette slot.
    Order matters: only a later-appearing label is bumped off a hash
    collision, so results stay deterministic for a given annotation order.
    """
    assigned = {}
    used = set()
    for label in labels_in_order:
        index = _palette_index_for_label(label)
        if index in used:
            probe = (index + 1) % len(PALETTE)
            while probe != index and probe in used:
                probe = (probe + 1) % len(PALETTE)
            index = probe
        used.add(index)
        assigned[label] = PALETTE[index]
    return assigned


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


# A shape whose own bounding box covers at least this fraction of the image
# is exempt from label-avoidance: a label overlapping part of a shape that
# large doesn't meaningfully hide it, and treating it as a must-avoid
# obstacle is what drives labels off-canvas on real dense/large-shape images.
LARGE_SHAPE_AREA_FRACTION = 0.25

# Relative cost weights for the placement search. Another label's box is a
# hard clash (unreadable text on text); another *shape* is only a soft one
# (a chip resting on a neighbouring outline is still readable), and drift is
# how far the canvas clamp had to pull a candidate away from the geometry it
# names — priced high enough that a slightly-overlapping but adjacent spot
# always beats a clean but distant one.
LABEL_CLASH_WEIGHT = 1.0
SHAPE_CLASH_WEIGHT = 0.15
DRIFT_WEIGHT = 40.0

# Cap on how many polygon vertices are used as label anchors. Real exports
# contain traced outlines with hundreds of points; every extra anchor is
# another candidate to score, and a coarse walk around the outline offers
# the same set of placements.
MAX_ANCHORS = 32


def _rect_overlap_area(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ox = max(0, min(ax2, bx2) - max(ax1, bx1))
    oy = max(0, min(ay2, by2) - max(ay1, by1))
    return ox * oy


def _clamp(value, low, high):
    return max(low, min(value, high))


def _shape_anchors(points, shape_type):
    # Anchors are points that lie on the shape as actually drawn, never on
    # its bounding box. For a long diagonal polygon (a scratch traced corner
    # to corner) the bbox corners sit in empty image, so anchoring a label
    # there is what makes it read as belonging to nothing.
    if shape_type == "bbox":
        x, y, w, h = points
        return [
            (x, y), (x + w / 2, y), (x + w, y),
            (x + w, y + h / 2), (x + w, y + h),
            (x + w / 2, y + h), (x, y + h), (x, y + h / 2),
        ]
    pts = [(float(p[0]), float(p[1])) for p in points]
    if len(pts) > MAX_ANCHORS:
        step = len(pts) / MAX_ANCHORS
        pts = [pts[int(i * step)] for i in range(MAX_ANCHORS)]
    return pts


def _centroid(anchors):
    return (
        sum(a[0] for a in anchors) / len(anchors),
        sum(a[1] for a in anchors) / len(anchors),
    )


def _label_candidates(anchors, centroid, box_w, box_h, gap):
    # One candidate per anchor per direction, each sitting immediately
    # outside the outline at that anchor: pushed radially away from the
    # shape's own centroid (so it clears the shape rather than covering it),
    # plus a straight-up variant for the conventional look. Sorted
    # topmost-first so the preferred resting place is above the shape.
    ccx, ccy = centroid
    candidates = []
    for ax, ay in anchors:
        dx, dy = ax - ccx, ay - ccy
        norm = math.hypot(dx, dy)
        directions = [(0.0, -1.0)]
        if norm > 1e-6:
            directions.insert(0, (dx / norm, dy / norm))
        for ux, uy in directions:
            candidates.append(
                (
                    ax + ux * (box_w / 2 + gap) - box_w / 2,
                    ay + uy * (box_h / 2 + gap) - box_h / 2,
                )
            )
    candidates.sort(key=lambda c: c[1])
    return candidates


def _best_label_rect(candidates, box_w, box_h, img_w, img_h, avoid):
    best_rect = None
    best_cost = None
    for want_x, want_y in candidates:
        box_x = _clamp(int(round(want_x)), 0, max(0, img_w - box_w))
        box_y = _clamp(int(round(want_y)), 0, max(0, img_h - box_h))
        rect = [box_x, box_y, box_x + box_w, box_y + box_h]
        cost = sum(weight * _rect_overlap_area(rect, other) for other, weight in avoid)
        cost += DRIFT_WEIGHT * (abs(box_x - want_x) + abs(box_y - want_y))
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_rect = rect
        if cost == 0:
            break
    return best_rect


def draw_annotations(image, annotations):
    output = image.copy()
    overlay = output.copy()
    img_h, img_w = output.shape[:2]

    dim = max(img_h, img_w)
    thickness = max(1, round(dim / 500))
    # Label text scales with the image so it stays legible after the viewer
    # scales a large photo down to fit, but is floored/capped so it never
    # vanishes on a small image or balloons on a huge one.
    font_scale = _clamp(dim / 2050, 0.45, 1.2)
    # One font size and one stroke weight for every label in the image:
    # a per-label shrink in dense clusters made the sizing look arbitrary,
    # so collisions there are now solved by position alone and any residual
    # label-on-label overlap is accepted.
    text_thickness = max(1, round(font_scale))

    distinct_labels = []
    seen_labels = set()
    for ann in annotations:
        if ann["label"] not in seen_labels:
            seen_labels.add(ann["label"])
            distinct_labels.append(ann["label"])
    label_colors = _assign_label_colors(distinct_labels)
    colors = [label_colors[ann["label"]] for ann in annotations]

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

    shape_bboxes = [
        _shape_bbox(ann["points"], ann["shape_type"]) for ann in annotations
    ]
    shape_anchors = [
        _shape_anchors(ann["points"], ann["shape_type"]) for ann in annotations
    ]

    image_area = img_w * img_h
    avoidable_shapes = [
        (index, b)
        for index, b in enumerate(shape_bboxes)
        if (b[2] - b[0]) * (b[3] - b[1]) <= LARGE_SHAPE_AREA_FRACTION * image_area
    ]

    # Labels are placed in a second pass, ordered top-to-bottom, so each new
    # label can be pushed clear of every label already placed above it —
    # this is what prevents nearby annotations' labels from stacking on top
    # of each other on densely-annotated images.
    order = sorted(range(len(annotations)), key=lambda i: shape_bboxes[i][1])
    placed = []
    pad_x = max(2, round(font_scale * 3))
    pad_y = max(1, round(font_scale * 2))
    gap = max(2, round(thickness * 1.5))

    for i in order:
        ann = annotations[i]
        color = colors[i]
        label = ann["label"]
        anchors = shape_anchors[i]
        centroid = _centroid(anchors)
        # A shape is an obstacle for other shapes' labels, never for its own:
        # its bbox is mostly empty canvas for a thin diagonal polygon, and
        # forbidding that whole rectangle is what previously pushed the label
        # far away from the outline it names.
        avoid = [(rect, LABEL_CLASH_WEIGHT) for rect in placed]
        avoid += [
            (b, SHAPE_CLASH_WEIGHT) for index, b in avoidable_shapes if index != i
        ]

        (text_w, text_h), baseline = cv2.getTextSize(label, FONT, font_scale, text_thickness)
        box_w = text_w + 2 * pad_x
        box_h = text_h + baseline + 2 * pad_y
        candidates = _label_candidates(anchors, centroid, box_w, box_h, gap)
        rect = _best_label_rect(candidates, box_w, box_h, img_w, img_h, avoid)

        placed.append(tuple(rect))

        # A filled chip in the shape's own colour with auto-contrast text:
        # the label has to stay readable over an arbitrary photo, and a
        # text-only halo turns to mush at small sizes because the outline
        # stroke eats into the glyph. The chip also ties the label to its
        # shape by colour, which matters once two labels sit side by side.
        cv2.rectangle(output, (rect[0], rect[1]), (rect[2], rect[3]), color, -1)
        cv2.putText(
            output,
            label,
            (rect[0] + pad_x, rect[3] - pad_y - baseline),
            FONT,
            font_scale,
            _text_color_for(color),
            text_thickness,
            cv2.LINE_AA,
        )

    return output
