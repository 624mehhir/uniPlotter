import json
import os

from app.schema import ParseError, ParseResult


def parse(annotation_bytes, image_width, image_height, image_filename):
    try:
        data = json.loads(annotation_bytes)
    except json.JSONDecodeError:
        raise ParseError("This doesn't look like valid JSON.")

    if not isinstance(data, dict) or "shapes" not in data:
        raise ParseError(
            "This doesn't look like valid LabelMe JSON — expected an object "
            "with a 'shapes' key."
        )

    warnings = []

    recorded_path = data.get("imagePath")
    if recorded_path:
        recorded_base = os.path.basename(recorded_path).lower()
        uploaded_base = os.path.basename(image_filename).lower()
        if recorded_base != uploaded_base:
            warnings.append(
                f"LabelMe records image '{recorded_path}' but the uploaded "
                f"file is '{image_filename}'; proceeding anyway."
            )

    recorded_width = data.get("imageWidth")
    recorded_height = data.get("imageHeight")
    if (
        recorded_width is not None
        and recorded_height is not None
        and (recorded_width, recorded_height) != (image_width, image_height)
    ):
        warnings.append(
            f"LabelMe records {recorded_width}x{recorded_height} but the "
            f"uploaded image is {image_width}x{image_height}."
        )

    annotations = []
    skipped_count = 0
    unsupported_shape_types = set()

    for shape in data["shapes"]:
        label = shape.get("label") or "unknown"
        shape_type = shape.get("shape_type")
        points = shape.get("points", [])

        if shape_type == "polygon":
            annotations.append(
                {
                    "label": label,
                    "shape_type": "polygon",
                    "points": [[x, y] for x, y in points],
                }
            )
        elif shape_type == "rectangle":
            (x1, y1), (x2, y2) = points[0], points[1]
            x_min, y_min = min(x1, x2), min(y1, y2)
            width, height = abs(x2 - x1), abs(y2 - y1)
            annotations.append(
                {
                    "label": label,
                    "shape_type": "bbox",
                    "points": [x_min, y_min, width, height],
                }
            )
        else:
            unsupported_shape_types.add(shape_type or "unknown")
            skipped_count += 1

    if unsupported_shape_types:
        warnings.append(
            f"Skipped {skipped_count} unsupported shape(s): "
            f"{', '.join(sorted(str(t) for t in unsupported_shape_types))}."
        )

    return ParseResult(
        annotations=annotations, warnings=warnings, skipped_count=skipped_count
    )
