import os
import xml.etree.ElementTree as ET

from app.schema import ParseError, ParseResult


def _select_image(images, uploaded_filename):
    uploaded_base = os.path.basename(uploaded_filename).lower()
    warnings = []

    for image in images:
        recorded_base = os.path.basename(image.get("name", "")).lower()
        if recorded_base == uploaded_base:
            return image, warnings

    if len(images) == 1:
        image = images[0]
        warnings.append(
            f"Uploaded filename '{uploaded_filename}' does not match the "
            f"CVAT file's recorded image '{image.get('name')}'; proceeding "
            f"with the only image entry present."
        )
        return image, warnings

    available = ", ".join(image.get("name", "") for image in images)
    raise ParseError(
        f"No image entry in the CVAT file matches uploaded filename "
        f"'{uploaded_filename}'. Available images: {available}"
    )


def parse(annotation_bytes, image_width, image_height, image_filename):
    try:
        root = ET.fromstring(annotation_bytes)
    except ET.ParseError:
        raise ParseError("This doesn't look like valid XML.")

    if root.tag != "annotations":
        raise ParseError(
            "This doesn't look like valid CVAT XML — expected an "
            "<annotations> root element."
        )

    if root.find("track") is not None:
        raise ParseError(
            "This is a CVAT video/interpolation export (<track> elements) — "
            "only image exports are supported."
        )

    images = root.findall("image")
    if not images:
        raise ParseError("CVAT file has no <image> elements.")

    selected_image, warnings = _select_image(images, image_filename)

    recorded_width = selected_image.get("width")
    recorded_height = selected_image.get("height")
    if recorded_width is not None and recorded_height is not None:
        recorded_width, recorded_height = int(recorded_width), int(recorded_height)
        if (recorded_width, recorded_height) != (image_width, image_height):
            warnings.append(
                f"CVAT records {recorded_width}x{recorded_height} but the "
                f"uploaded image is {image_width}x{image_height}."
            )

    annotations = []
    skipped_count = 0
    unsupported_shape_types = set()
    rotated_count = 0
    malformed_count = 0

    for child in selected_image:
        label = child.get("label", "unknown")
        rotation = child.get("rotation")
        try:
            if rotation and float(rotation) != 0:
                rotated_count += 1
        except ValueError:
            pass

        if child.tag == "box":
            try:
                xtl = float(child.get("xtl"))
                ytl = float(child.get("ytl"))
                xbr = float(child.get("xbr"))
                ybr = float(child.get("ybr"))
            except (TypeError, ValueError):
                malformed_count += 1
                skipped_count += 1
                continue
            annotations.append(
                {
                    "label": label,
                    "shape_type": "bbox",
                    "points": [xtl, ytl, xbr - xtl, ybr - ytl],
                }
            )
        elif child.tag == "polygon":
            points_str = child.get("points", "")
            try:
                points = [
                    [float(p) for p in pair.split(",")]
                    for pair in points_str.split(";")
                    if pair
                ]
                if not points or any(len(p) != 2 for p in points):
                    raise ValueError("polygon points must be x,y pairs")
            except ValueError:
                malformed_count += 1
                skipped_count += 1
                continue
            annotations.append(
                {"label": label, "shape_type": "polygon", "points": points}
            )
        else:
            unsupported_shape_types.add(child.tag)
            skipped_count += 1

    if unsupported_shape_types:
        warnings.append(
            f"Skipped {skipped_count - malformed_count} unsupported shape(s): "
            f"{', '.join(sorted(unsupported_shape_types))}."
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
