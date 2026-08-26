import os
import xml.etree.ElementTree as ET

from app.schema import ParseError, ParseResult


def parse(annotation_bytes, image_width, image_height, image_filename):
    try:
        root = ET.fromstring(annotation_bytes)
    except ET.ParseError:
        raise ParseError("This doesn't look like valid XML.")

    if root.tag != "annotation":
        raise ParseError(
            "This doesn't look like valid Pascal VOC XML — expected an "
            "<annotation> root element."
        )

    warnings = []

    recorded_filename = root.findtext("filename")
    if recorded_filename:
        recorded_base = os.path.basename(recorded_filename).lower()
        uploaded_base = os.path.basename(image_filename).lower()
        if recorded_base != uploaded_base:
            warnings.append(
                f"VOC records image '{recorded_filename}' but the uploaded "
                f"file is '{image_filename}'; proceeding anyway."
            )

    size_elem = root.find("size")
    if size_elem is not None:
        recorded_width = size_elem.findtext("width")
        recorded_height = size_elem.findtext("height")
        if recorded_width is not None and recorded_height is not None:
            try:
                recorded_width, recorded_height = int(recorded_width), int(recorded_height)
            except ValueError:
                warnings.append(
                    "VOC <size> width/height could not be parsed as numbers; "
                    "skipping the dimension check."
                )
            else:
                if (recorded_width, recorded_height) != (image_width, image_height):
                    warnings.append(
                        f"VOC records {recorded_width}x{recorded_height} but the "
                        f"uploaded image is {image_width}x{image_height}."
                    )

    annotations = []
    skipped_count = 0
    for obj in root.findall("object"):
        bndbox = obj.find("bndbox")
        if bndbox is None:
            continue
        label = obj.findtext("name") or "unknown"
        try:
            xmin = float(bndbox.findtext("xmin"))
            ymin = float(bndbox.findtext("ymin"))
            xmax = float(bndbox.findtext("xmax"))
            ymax = float(bndbox.findtext("ymax"))
        except (TypeError, ValueError):
            skipped_count += 1
            continue
        annotations.append(
            {
                "label": label,
                "shape_type": "bbox",
                "points": [xmin, ymin, xmax - xmin, ymax - ymin],
            }
        )

    if skipped_count:
        warnings.append(
            f"Skipped {skipped_count} object(s) with missing/invalid bndbox "
            f"coordinates."
        )

    return ParseResult(
        annotations=annotations, warnings=warnings, skipped_count=skipped_count
    )
