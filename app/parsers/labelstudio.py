import json
import os

from app.schema import ParseError, ParseResult


def _select_task(tasks, uploaded_filename):
    uploaded_base = os.path.basename(uploaded_filename).lower()
    warnings = []

    for task in tasks:
        recorded = task.get("data", {}).get("image", "")
        if os.path.basename(recorded).lower() == uploaded_base:
            return task, warnings

    for task in tasks:
        recorded = task.get("data", {}).get("image", "")
        if os.path.basename(recorded).lower().endswith(uploaded_base):
            return task, warnings

    if len(tasks) == 1:
        task = tasks[0]
        recorded = task.get("data", {}).get("image")
        warnings.append(
            f"Uploaded filename '{uploaded_filename}' does not match the "
            f"Label Studio task's recorded image '{recorded}'; proceeding "
            f"with the only task present."
        )
        return task, warnings

    available = ", ".join(str(task.get("data", {}).get("image")) for task in tasks)
    raise ParseError(
        f"No task in the Label Studio file matches uploaded filename "
        f"'{uploaded_filename}'. Available images: {available}"
    )


def parse(annotation_bytes, image_width, image_height, image_filename):
    try:
        data = json.loads(annotation_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ParseError("This doesn't look like valid JSON.")

    if not isinstance(data, list) or not data:
        raise ParseError(
            "This doesn't look like valid Label Studio JSON — expected a "
            "non-empty list of tasks."
        )

    for task in data:
        if not isinstance(task, dict) or "data" not in task or "annotations" not in task:
            raise ParseError(
                "This looks like Label Studio's JSON-MIN export, which isn't "
                "supported — re-export using the full JSON format (each task "
                "needs 'data' and 'annotations' keys)."
            )

    task, warnings = _select_task(data, image_filename)

    results = []
    for annotation in task.get("annotations", []):
        results.extend(annotation.get("result", []))

    recorded_width = recorded_height = None
    for item in results:
        if item.get("original_width") and item.get("original_height"):
            recorded_width = item["original_width"]
            recorded_height = item["original_height"]
            break

    if recorded_width is not None and (recorded_width, recorded_height) != (
        image_width,
        image_height,
    ):
        warnings.append(
            f"Label Studio records {recorded_width}x{recorded_height} but "
            f"the uploaded image is {image_width}x{image_height}."
        )

    annotations = []
    skipped_count = 0
    unsupported_types = set()
    rotated_count = 0
    malformed_count = 0

    for item in results:
        item_type = item.get("type")
        value = item.get("value", {})
        orig_w = item.get("original_width") or image_width
        orig_h = item.get("original_height") or image_height

        if value.get("rotation"):
            rotated_count += 1

        if item_type == "polygonlabels":
            label_list = value.get("polygonlabels") or []
            label = label_list[0] if label_list else "unknown"
            try:
                points = [
                    [(x / 100) * orig_w, (y / 100) * orig_h]
                    for x, y in value.get("points", [])
                ]
                if not points:
                    raise ValueError("polygon has no points")
            except (TypeError, ValueError):
                malformed_count += 1
                skipped_count += 1
                continue
            annotations.append(
                {"label": label, "shape_type": "polygon", "points": points}
            )
        elif item_type == "rectanglelabels":
            label_list = value.get("rectanglelabels") or []
            label = label_list[0] if label_list else "unknown"
            try:
                x = ((value.get("x") or 0) / 100) * orig_w
                y = ((value.get("y") or 0) / 100) * orig_h
                width = ((value.get("width") or 0) / 100) * orig_w
                height = ((value.get("height") or 0) / 100) * orig_h
            except TypeError:
                malformed_count += 1
                skipped_count += 1
                continue
            annotations.append(
                {"label": label, "shape_type": "bbox", "points": [x, y, width, height]}
            )
        else:
            unsupported_types.add(item_type or "unknown")
            skipped_count += 1

    if unsupported_types:
        warnings.append(
            f"Skipped {skipped_count - malformed_count} unsupported shape(s): "
            f"{', '.join(sorted(str(t) for t in unsupported_types))}."
        )

    if malformed_count:
        warnings.append(
            f"Skipped {malformed_count} shape(s) with missing/invalid "
            f"coordinates."
        )

    if rotated_count:
        warnings.append(
            f"{rotated_count} shape(s) have a rotation attribute; drawn "
            f"axis-aligned (rotation isn't supported)."
        )

    return ParseResult(
        annotations=annotations, warnings=warnings, skipped_count=skipped_count
    )
