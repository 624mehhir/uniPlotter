import json
import os

from app.schema import ParseError, ParseResult


def _find_images(data):
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise ParseError(
            "This doesn't look like a valid Lekhana export — 'tasks' must "
            "be a list."
        )

    found = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        images = task.get("images")
        if not isinstance(images, list):
            continue
        for image in images:
            if isinstance(image, dict):
                found.append(image)
    return found


def _select_image(images, uploaded_filename):
    uploaded_base = os.path.basename(uploaded_filename).lower()
    warnings = []

    for image in images:
        recorded = image.get("data", {}).get("filename", "")
        if os.path.basename(recorded).lower() == uploaded_base:
            return image, warnings

    if len(images) == 1:
        image = images[0]
        recorded = image.get("data", {}).get("filename")
        warnings.append(
            f"Uploaded filename '{uploaded_filename}' does not match the "
            f"Lekhana file's recorded filename '{recorded}'; proceeding "
            f"with the only image entry present."
        )
        return image, warnings

    available = ", ".join(
        str(image.get("data", {}).get("filename")) for image in images
    )
    raise ParseError(
        f"No image entry in the Lekhana file matches uploaded filename "
        f"'{uploaded_filename}'. Available images: {available}"
    )


def parse(annotation_bytes, image_width, image_height, image_filename):
    try:
        data = json.loads(annotation_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ParseError("This doesn't look like valid JSON.")

    if not isinstance(data, dict) or "tasks" not in data:
        raise ParseError(
            "This doesn't look like a valid Lekhana export — expected an "
            "object with a 'tasks' key."
        )

    images = _find_images(data)
    if not images:
        raise ParseError("Lekhana file contains no images across its tasks.")

    selected_image, warnings = _select_image(images, image_filename)
    image_data = selected_image.get("data") or {}

    recorded_width = image_data.get("width")
    recorded_height = image_data.get("height")
    if (
        recorded_width is not None
        and recorded_height is not None
        and (recorded_width, recorded_height) != (image_width, image_height)
    ):
        warnings.append(
            f"Lekhana records {recorded_width}x{recorded_height} but the "
            f"uploaded image is {image_width}x{image_height}."
        )

    output = selected_image.get("output")
    if not isinstance(output, dict):
        raise ParseError(
            "Selected image has no usable 'output' object with annotations."
        )

    has_annotations = "annotations" in output
    has_layers = "layers" in output

    if has_annotations and has_layers:
        raise ParseError(
            "Selected image's 'output' has both 'annotations' and 'layers' "
            "— expected exactly one."
        )
    elif has_annotations:
        raw_annotations = output.get("annotations")
        if not isinstance(raw_annotations, list):
            raise ParseError("'output.annotations' is not a list.")
    elif has_layers:
        layers = output.get("layers")
        if not isinstance(layers, dict):
            raise ParseError("'output.layers' is not an object.")
        raw_annotations = []
        for layer_annotations in layers.values():
            if isinstance(layer_annotations, list):
                raw_annotations.extend(layer_annotations)
    else:
        raise ParseError(
            "Selected image's 'output' has neither 'annotations' nor "
            "'layers' — unrecognized output structure."
        )

    annotations = []
    skipped_count = 0
    unsupported_types = set()
    malformed_count = 0

    for ann in raw_annotations:
        if not isinstance(ann, dict):
            malformed_count += 1
            skipped_count += 1
            continue

        label = ann.get("label") or "unknown"
        ann_type = ann.get("type")
        geometry = ann.get("geometry")

        if ann_type == "bbox":
            if not isinstance(geometry, dict):
                malformed_count += 1
                skipped_count += 1
                continue
            try:
                points = [
                    float(geometry["x"]),
                    float(geometry["y"]),
                    float(geometry["width"]),
                    float(geometry["height"]),
                ]
            except (KeyError, TypeError, ValueError):
                malformed_count += 1
                skipped_count += 1
                continue
            annotations.append(
                {"label": label, "shape_type": "bbox", "points": points}
            )
        elif ann_type == "polygon":
            if not isinstance(geometry, dict):
                malformed_count += 1
                skipped_count += 1
                continue
            try:
                polygon_points = [
                    [float(x), float(y)] for x, y in geometry["points"]
                ]
                if not polygon_points:
                    raise ValueError("polygon has no points")
            except (KeyError, TypeError, ValueError):
                malformed_count += 1
                skipped_count += 1
                continue
            annotations.append(
                {
                    "label": label,
                    "shape_type": "polygon",
                    "points": polygon_points,
                }
            )
        elif ann_type == "brush":
            if isinstance(geometry, dict) and set(geometry.keys()) == {"points"}:
                try:
                    polygon_points = [
                        [float(x), float(y)] for x, y in geometry["points"]
                    ]
                    if not polygon_points:
                        raise ValueError("brush outline has no points")
                except (KeyError, TypeError, ValueError):
                    malformed_count += 1
                    skipped_count += 1
                    continue
                annotations.append(
                    {
                        "label": label,
                        "shape_type": "polygon",
                        "points": polygon_points,
                    }
                )
            else:
                unsupported_types.add("brush (freehand)")
                skipped_count += 1
        else:
            unsupported_types.add(str(ann_type) if ann_type else "unknown")
            skipped_count += 1

    if unsupported_types:
        warnings.append(
            f"Skipped {skipped_count - malformed_count} unsupported "
            f"shape(s): {', '.join(sorted(unsupported_types))}."
        )

    if malformed_count:
        warnings.append(
            f"Skipped {malformed_count} annotation(s) with missing/invalid "
            f"geometry."
        )

    return ParseResult(
        annotations=annotations, warnings=warnings, skipped_count=skipped_count
    )
