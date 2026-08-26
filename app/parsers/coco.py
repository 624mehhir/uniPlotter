import json
import os

from app.schema import ParseError, ParseResult


def _select_image(images, uploaded_filename):
    uploaded_base = os.path.basename(uploaded_filename).lower()
    warnings = []

    for image in images:
        recorded_base = os.path.basename(image.get("file_name", "")).lower()
        if recorded_base == uploaded_base:
            return image, warnings

    if len(images) == 1:
        image = images[0]
        warnings.append(
            f"Uploaded filename '{uploaded_filename}' does not match the COCO "
            f"file's recorded filename '{image.get('file_name')}'; proceeding "
            f"with the only image entry present."
        )
        return image, warnings

    available = ", ".join(str(image.get("file_name")) for image in images)
    raise ParseError(
        f"No image entry in the COCO file matches uploaded filename "
        f"'{uploaded_filename}'. Available images: {available}"
    )


def parse(annotation_bytes, image_width, image_height, image_filename):
    try:
        data = json.loads(annotation_bytes)
    except json.JSONDecodeError:
        raise ParseError("This doesn't look like valid JSON.")

    if not isinstance(data, dict) or not all(
        key in data for key in ("images", "annotations", "categories")
    ):
        raise ParseError(
            "This doesn't look like valid COCO JSON — expected an object "
            "with 'images', 'annotations', and 'categories' keys."
        )

    images = data["images"]
    if not images:
        raise ParseError("COCO file's 'images' list is empty.")

    selected_image, warnings = _select_image(images, image_filename)
    selected_image_id = selected_image.get("id")

    recorded_width = selected_image.get("width")
    recorded_height = selected_image.get("height")
    if (recorded_width, recorded_height) != (image_width, image_height) and (
        recorded_width is not None and recorded_height is not None
    ):
        warnings.append(
            f"COCO records {recorded_width}x{recorded_height} but the "
            f"uploaded image is {image_width}x{image_height}."
        )

    category_names = {
        category.get("id"): category.get("name")
        for category in data["categories"]
    }

    annotations = []
    skipped_count = 0
    unknown_category_ids = set()
    unsupported_shape_types = set()

    for ann in data["annotations"]:
        if ann.get("image_id") != selected_image_id:
            continue

        category_id = ann.get("category_id")
        label = category_names.get(category_id)
        if label is None:
            label = f"unknown:{category_id}"
            unknown_category_ids.add(category_id)

        segmentation = ann.get("segmentation")

        if isinstance(segmentation, dict):
            unsupported_shape_types.add("RLE segmentation")
            skipped_count += 1
            segmentation = None

        if isinstance(segmentation, list) and len(segmentation) > 0:
            for part in segmentation:
                points = [
                    [part[i], part[i + 1]] for i in range(0, len(part) - 1, 2)
                ]
                annotations.append(
                    {"label": label, "shape_type": "polygon", "points": points}
                )
        else:
            bbox = ann.get("bbox")
            if bbox and len(bbox) == 4:
                annotations.append(
                    {"label": label, "shape_type": "bbox", "points": list(bbox)}
                )

    if unknown_category_ids:
        warnings.append(
            f"Unknown category id(s) {sorted(unknown_category_ids)} — "
            f"labeled as 'unknown:<id>'."
        )

    if unsupported_shape_types:
        warnings.append(
            f"Skipped {skipped_count} unsupported shape(s): "
            f"{', '.join(sorted(unsupported_shape_types))}."
        )

    return ParseResult(
        annotations=annotations, warnings=warnings, skipped_count=skipped_count
    )
